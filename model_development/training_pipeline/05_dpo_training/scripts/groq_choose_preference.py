"""
Groq API (Llama 3.1 70B)로 페르소나 기준으로 variant A/B 중 chosen/rejected 결정
"""

from groq import Groq
import json
import yaml
from pathlib import Path
from tqdm import tqdm
import argparse
import os
import time


class GroqChooser:
    def __init__(self, api_key: str, personas_config: str):
        self.client = Groq(api_key=api_key)
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds = 30 req/min

        with open(personas_config) as f:
            self.personas = yaml.safe_load(f)['personas']

        print(f"✅ Loaded {len(self.personas)} personas for evaluation")
        print(f"📊 Rate limit: 30 req/min (2 sec delay between requests)")

    def _rate_limit(self):
        """Rate limiting: 30 requests/minute"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def choose_preference(self, prompt: str, variant_a: str, variant_b: str, persona: dict):
        """
        Groq (Llama 3.1 70B)로 variant A와 B 중 chosen/rejected 결정

        Returns:
            (chosen, rejected, evaluation)
        """

        # Clean variants (remove extra tokens)
        def clean_variant(variant: str) -> str:
            """Remove extra tokens like <|eot_id|>, <|start_header_id|>, etc."""
            # Find the end of JSON (after the closing brace)
            if '}<|' in variant:
                variant = variant.split('}<|')[0] + '}'
            return variant.strip()

        variant_a = clean_variant(variant_a)
        variant_b = clean_variant(variant_b)

        # JSON 파싱
        try:
            recipe_a = json.loads(variant_a)
            recipe_b = json.loads(variant_b)
        except json.JSONDecodeError as e:
            return None, None, {"error": "json_decode_failed", "details": str(e)}

        # User message 추출
        user_message = prompt.split('<|im_start|>user')[1].split('<|im_end|>')[0].strip()

        evaluation_prompt = f"""You are an expert recipe evaluator. Given a user's persona and two recipe variants, determine which one better aligns with the persona.

**User Persona:**
- Name: {persona['name']}
- Dietary Restrictions: {persona.get('dietary_restrictions', 'None')}
- Forbidden Ingredients: {', '.join(persona.get('forbidden_keywords', []))}
- Preferred Cuisines: {', '.join(persona.get('preferences', {}).get('cuisine', []))}
- Preference Keywords: {', '.join(persona.get('preference_keywords', []))}

**User Request:**
{user_message}

**Variant A:**
```json
{json.dumps(recipe_a, indent=2, ensure_ascii=False)}
```

**Variant B:**
```json
{json.dumps(recipe_b, indent=2, ensure_ascii=False)}
```

**Evaluation Task:**

1. **Evaluate Variant A** (score 1-10):
   - Dietary restrictions respected?
   - Forbidden ingredients avoided?
   - Cuisine/flavor preferences matched?
   - Overall persona alignment?

2. **Evaluate Variant B** (score 1-10):
   - Same criteria as Variant A

3. **Determine Chosen/Rejected**:
   - **Chosen**: The variant that BETTER aligns with the persona
   - **Rejected**: The variant that is LESS aligned (or violates constraints)
   - If both are good, choose the better one
   - If both are bad, choose the less bad one

**Output Format (JSON):**
```json
{{
  "variant_a_evaluation": {{
    "alignment_score": 1-10,
    "violations": ["list any violations"],
    "strengths": ["what it does well"],
    "reasoning": "explanation"
  }},
  "variant_b_evaluation": {{
    "alignment_score": 1-10,
    "violations": ["list any violations"],
    "strengths": ["what it does well"],
    "reasoning": "explanation"
  }},
  "chosen_variant": "A" or "B",
  "rejected_variant": "A" or "B",
  "confidence": "high" or "medium" or "low",
  "overall_reasoning": "Why chosen is better than rejected for this persona",
  "recommendation": "use_pair" or "reject_pair"
}}
```

**Notes:**
- If both variants have similar scores (difference < 2), set confidence="low"
- If one clearly violates dietary restrictions, it should be "rejected"
- If both are terrible (both score < 5), set recommendation="reject_pair"
- If both are excellent but indistinguishable, choose based on minor details

IMPORTANT: You MUST respond with ONLY valid JSON. Do not include any text before or after the JSON object."""

        try:
            # Rate limiting
            self._rate_limit()

            # Groq API 호출
            # Updated model: llama-3.1-70b-versatile is decommissioned
            # Using llama-3.3-70b-versatile (newer, better model)
            chat_completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert recipe evaluator. You MUST respond with ONLY valid JSON, no additional text."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            response_content = chat_completion.choices[0].message.content
            evaluation = json.loads(response_content)

            # Chosen/Rejected 할당
            chosen_variant = evaluation['chosen_variant']
            rejected_variant = evaluation['rejected_variant']

            chosen = variant_a if chosen_variant == 'A' else variant_b
            rejected = variant_a if rejected_variant == 'A' else variant_b

            return chosen, rejected, evaluation

        except Exception as e:
            print(f"\nGroq API Error: {e}")
            return None, None, {"error": str(e)}

    def process_persona_variants(self, input_file: Path, output_file: Path):
        """
        페르소나별 variants를 Groq로 평가하고 chosen/rejected 결정
        """
        # Variants 로드
        variants = []
        with open(input_file, encoding='utf-8') as f:
            for line in f:
                variants.append(json.loads(line))

        print(f"\nProcessing {len(variants)} variant pairs...")

        final_pairs = []
        rejected_pairs = []

        for sample in tqdm(variants, desc="Groq Choosing"):
            persona_id = sample['metadata']['persona']
            persona = self.personas[persona_id]

            chosen, rejected, evaluation = self.choose_preference(
                sample['prompt'],
                sample['variant_a'],
                sample['variant_b'],
                persona
            )

            if chosen and rejected:
                # 품질 체크
                if evaluation.get('recommendation') == 'use_pair':
                    # DPO 페어로 저장
                    final_pairs.append({
                        "prompt": sample['prompt'],
                        "chosen": chosen,
                        "rejected": rejected,
                        "metadata": {
                            **sample['metadata'],
                            "evaluation": evaluation
                        }
                    })
                else:
                    rejected_pairs.append({
                        "reason": "groq_recommendation_reject",
                        "sample": sample,
                        "evaluation": evaluation
                    })
            else:
                rejected_pairs.append({
                    "reason": "evaluation_failed",
                    "sample": sample,
                    "evaluation": evaluation
                })

        # 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            for pair in final_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + '\n')

        rejected_log = output_file.parent / f"{output_file.stem}_rejected.jsonl"
        with open(rejected_log, 'w', encoding='utf-8') as f:
            for pair in rejected_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + '\n')

        print(f"\n{'='*60}")
        print(f"✅ Final DPO pairs: {len(final_pairs)}")
        print(f"❌ Rejected pairs: {len(rejected_pairs)}")
        print(f"📊 Pass rate: {len(final_pairs)/len(variants)*100:.1f}%")
        print(f"{'='*60}\n")

        return final_pairs


def main():
    parser = argparse.ArgumentParser(description="Groq (Llama 3.1 70B) chooses chosen/rejected from variants")
    parser.add_argument("--personas_config", default="personas.yaml",
                       help="Personas configuration file")
    parser.add_argument("--input_dir", default="../../data/dpo_variants",
                       help="Input directory with variant files")
    parser.add_argument("--output_dir", default="../../data/dpo_final_pairs",
                       help="Output directory for DPO pairs")
    parser.add_argument("--persona", type=str, default=None,
                       help="Process specific persona only (optional)")
    args = parser.parse_args()

    # API Key 확인
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set")
        print("Please set it: export GROQ_API_KEY='your_key'")
        print("\nGet your free API key at: https://console.groq.com/keys")
        return

    chooser = GroqChooser(
        api_key=api_key,
        personas_config=args.personas_config
    )

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 처리할 파일 결정
    if args.persona:
        input_files = [input_dir / f"{args.persona}_variants.jsonl"]
        if not input_files[0].exists():
            print(f"Error: File not found: {input_files[0]}")
            return
    else:
        input_files = list(input_dir.glob("*_variants.jsonl"))

    if not input_files:
        print(f"Error: No variant files found in {input_dir}")
        return

    print(f"\nWill process {len(input_files)} persona(s)")
    print(f"Using Groq API with Llama 3.1 70B\n")

    total_final = 0
    total_rejected = 0

    for input_file in input_files:
        persona_id = input_file.stem.replace("_variants", "")
        output_file = output_dir / f"{persona_id}_dpo_pairs.jsonl"

        print(f"\n{'='*60}")
        print(f"Processing {persona_id}")
        print(f"{'='*60}")

        final_pairs = chooser.process_persona_variants(input_file, output_file)

        total_final += len(final_pairs)

    print(f"\n{'='*60}")
    print(f"🎉 All personas processed!")
    print(f"Total final DPO pairs: {total_final}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
