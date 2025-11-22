"""
페르소나별로 프롬프트 생성 + 2개 variants 생성
GPT-4가 나중에 chosen/rejected 결정
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import yaml
import json
from typing import Dict, List
from tqdm import tqdm
import random
from pathlib import Path
import argparse


class VariantGenerator:
    def __init__(self, base_model_path: str, adapter_path: str, personas_config: str):
        print(f"Loading model from {base_model_path} with adapter {adapter_path}...")

        # Device 설정 (MPS for M1/M2 Mac)
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
            print("🚀 Using MPS (Metal Performance Shaders) for acceleration")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            print("🚀 Using CUDA GPU")
        else:
            self.device = torch.device("cpu")
            print("⚠️  Using CPU (slow)")

        # 모델 로드
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token

        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True
        )
        self.model = PeftModel.from_pretrained(self.base_model, adapter_path)
        self.model = self.model.to(self.device)
        self.model.eval()

        print("✅ Model loaded successfully")

        # 페르소나 로드
        with open(personas_config) as f:
            self.personas = yaml.safe_load(f)['personas']

        print(f"✅ Loaded {len(self.personas)} personas")

    def create_user_message(self, inventory: List[str], persona: Dict) -> str:
        """
        페르소나 기반 user message 생성
        """
        inventory_str = ", ".join(inventory)
        message = f"I have {inventory_str}."

        # 페르소나 선호도 반영
        if persona.get('preferences', {}).get('cuisine'):
            cuisine = random.choice(persona['preferences']['cuisine'])
            message += f" I want a {cuisine} recipe."

        # 식이 제약 반영
        if persona.get('dietary_restrictions'):
            restriction = random.choice(persona['dietary_restrictions'])
            phrasing = random.choice([
                f" I want a {restriction} recipe.",
                f" I'm {restriction}, what can I cook?",
                f" {restriction.capitalize()} recipe please."
            ])
            message += phrasing

        return message

    def create_chatml_prompt(self, user_message: str, persona: Dict,
                            enforce_constraints: bool = True) -> str:
        """
        ChatML 형식 프롬프트 생성

        Args:
            enforce_constraints: True면 페르소나 제약 명시, False면 일반적인 프롬프트
        """
        # System prompt
        system_prompt = "You are a recipe generation AI that creates recipes based on user inventory and preferences."

        if enforce_constraints:
            # 페르소나 제약 강하게 적용

            # 1. Cuisine preference (추가)
            if persona.get('preferences', {}).get('cuisine'):
                cuisines = ", ".join(persona['preferences']['cuisine'])
                system_prompt += f" You specialize in {cuisines} cuisine."

            # 2. Flavor profile (추가)
            if persona.get('preferences', {}).get('flavor_profile'):
                flavors = ", ".join(persona['preferences']['flavor_profile'])
                system_prompt += f" You prefer {flavors} flavors."

            # 3. Preferred ingredients (추가)
            if persona.get('preference_keywords'):
                keywords = ", ".join(persona['preference_keywords'][:5])
                system_prompt += f" Try to incorporate ingredients like: {keywords}."

            # 4. Dietary restrictions (기존)
            if persona.get('dietary_restrictions'):
                restrictions = ", ".join(persona['dietary_restrictions'])
                system_prompt += f" The user is {restrictions}."

            # 5. Forbidden ingredients (기존)
            if persona.get('forbidden_keywords'):
                forbidden = ", ".join(persona['forbidden_keywords'][:5])
                system_prompt += f" Do NOT use these ingredients: {forbidden}."

        # ChatML 형식
        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_message}<|im_end|>
<|im_start|>assistant
"""

        return prompt

    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """
        레시피 생성 (JSON)
        """
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.convert_tokens_to_ids("<|im_end|>")
            )

        # Assistant 응답 추출
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)

        if "<|im_start|>assistant" in full_response:
            assistant_response = full_response.split("<|im_start|>assistant")[-1]
            assistant_response = assistant_response.replace("<|im_end|>", "").strip()
            return assistant_response

        return full_response

    def generate_2_variants(self, user_message: str, persona: Dict) -> tuple:
        """
        2개 variants 생성

        Variant A: 페르소나 제약 강하게 적용 (temperature=0.7)
        Variant B: 페르소나 제약 약하게 또는 없음 (temperature=0.9)

        Returns:
            (variant_a, variant_b, base_prompt)
        """
        # Variant A: 제약 강함
        prompt_a = self.create_chatml_prompt(user_message, persona, enforce_constraints=True)
        variant_a = self.generate_response(prompt_a, temperature=0.7)

        # Variant B: 제약 약함 (또는 더 다양한 출력)
        prompt_b = self.create_chatml_prompt(user_message, persona, enforce_constraints=False)
        variant_b = self.generate_response(prompt_b, temperature=0.9)

        # Base prompt (chosen/rejected 모두에 사용될 프롬프트)
        # Variant A의 prompt 사용 (제약이 명시된 버전)
        base_prompt = prompt_a

        return variant_a, variant_b, base_prompt

    def generate_for_persona(self, persona_id: str, count: int = 500):
        """
        페르소나별로 500개 × 2 variants 생성
        """
        persona = self.personas[persona_id]
        samples = []

        print(f"\n{'='*60}")
        print(f"Generating {count} samples for: {persona_id}")
        print(f"Persona: {persona['name']}")
        print(f"{'='*60}\n")

        for i in tqdm(range(count), desc=f"{persona_id}"):
            # 재료 선택
            inventory = self._get_compatible_inventory(persona, count=random.randint(5, 8))

            # User message 생성
            user_message = self.create_user_message(inventory, persona)

            # 2개 variants 생성
            try:
                variant_a, variant_b, base_prompt = self.generate_2_variants(user_message, persona)

                # 저장 (GPT-4가 나중에 chosen/rejected 결정)
                sample = {
                    "prompt": base_prompt,
                    "variant_a": variant_a,
                    "variant_b": variant_b,
                    "metadata": {
                        "persona": persona_id,
                        "user_message": user_message,
                        "inventory": inventory
                    }
                }

                samples.append(sample)
            except Exception as e:
                print(f"\nError generating sample {i}: {e}")
                continue

        return samples

    def _get_compatible_inventory(self, persona: Dict, count: int) -> List[str]:
        """
        페르소나 호환 재료 선택
        """
        all_ingredients = [
            "tofu", "chicken", "beef", "pork", "salmon", "shrimp", "eggs",
            "rice", "pasta", "bread", "quinoa", "couscous", "flour", "noodles",
            "onion", "garlic", "tomato", "bell pepper", "broccoli", "carrot",
            "spinach", "mushroom", "lettuce", "cucumber", "potato", "corn",
            "olive oil", "butter", "cheese", "milk", "yogurt",
            "soy sauce", "salt", "pepper", "ginger", "basil", "oregano",
            "beans", "lentils", "chickpeas", "avocado", "lime", "cilantro",
            "eggplant", "zucchini", "cabbage", "kale", "cauliflower",
            "green beans", "peas", "celery", "leek", "scallion"
        ]

        # Forbidden keywords 제외
        forbidden = [kw.lower() for kw in persona.get('forbidden_keywords', [])]
        compatible = [
            ing for ing in all_ingredients
            if not any(f in ing.lower() for f in forbidden)
        ]

        # 랜덤 선택
        if len(compatible) < count:
            selected = compatible
        else:
            selected = random.sample(compatible, count)

        # 선호 재료 일부 포함 (30% 확률)
        preferred = persona.get('preference_keywords', [])
        if preferred and random.random() < 0.3:
            pref_candidates = [p for p in preferred if p in all_ingredients]
            if pref_candidates:
                pref_ing = random.choice(pref_candidates)
                if pref_ing not in selected and len(selected) > 0:
                    selected[0] = pref_ing

        return selected


def main():
    parser = argparse.ArgumentParser(description="Generate DPO variant pairs for personas")
    parser.add_argument("--base_model", default="meta-llama/Llama-3.2-3B-Instruct",
                       help="Base model path")
    parser.add_argument("--adapter", default="../04_training/llama3b_lambda_lora",
                       help="LoRA adapter path (relative to 04_training)")
    parser.add_argument("--personas_config", default="../05_dpo_training/personas.yaml",
                       help="Personas configuration file")
    parser.add_argument("--output_dir", default="../05_dpo_training/data/variants",
                       help="Output directory for variants")
    parser.add_argument("--count", type=int, default=500,
                       help="Number of samples per persona")
    parser.add_argument("--persona", type=str, default=None,
                       help="Generate for specific persona only (optional)")
    args = parser.parse_args()

    # 생성기 초기화
    generator = VariantGenerator(
        args.base_model,
        args.adapter,
        args.personas_config
    )

    # 출력 디렉토리
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 생성할 페르소나 결정
    if args.persona:
        personas_to_generate = [args.persona] if args.persona in generator.personas else []
        if not personas_to_generate:
            print(f"Error: Persona '{args.persona}' not found in config")
            return
    else:
        personas_to_generate = list(generator.personas.keys())

    print(f"\nWill generate variants for {len(personas_to_generate)} persona(s)")
    print(f"Samples per persona: {args.count}")
    print(f"Total samples: {len(personas_to_generate) * args.count * 2} (2 variants each)\n")

    # 각 페르소나별 생성
    for persona_id in personas_to_generate:
        samples = generator.generate_for_persona(persona_id, args.count)

        # 저장
        output_file = output_dir / f"{persona_id}_variants.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

        print(f"✅ Saved {len(samples)} samples to {output_file}\n")

    print("\n🎉 Variant generation complete!")


if __name__ == "__main__":
    main()
