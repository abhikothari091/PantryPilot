"""
PyTorch Model Service with Llama 3B + LoRA adapter
Supports base model vs fine-tuned model comparison
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from pathlib import Path
from typing import List, Dict, Optional


class ModelService:
    def __init__(self, base_model_id: str, adapter_path: str):
        """
        Initialize model service with Llama 3B base model and LoRA adapter

        Args:
            base_model_id: HuggingFace model ID (meta-llama/Llama-3.2-3B-Instruct)
            adapter_path: Path to LoRA adapter weights
        """
        self.base_model_id = base_model_id
        self.adapter_path = adapter_path
        self.device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"

        print(f"🖥️  Using device: {self.device}")
        print(f"📥 Loading base model: {base_model_id}")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)

        # Load base model
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            torch_dtype=torch.float16,
        ).to(self.device) # Explicitly move to device

        print(f"✅ Base model loaded (~6GB memory)")

        # Load fine-tuned model with LoRA adapter
        if Path(adapter_path).exists():
            print(f"📥 Loading LoRA adapter: {adapter_path}")
            self.finetuned_model = PeftModel.from_pretrained(self.base_model, adapter_path)
            self.finetuned_model.eval()
            print(f"✅ Fine-tuned model loaded (base + 35MB adapter)")
        else:
            print(f"⚠️  LoRA adapter not found at {adapter_path}")
            self.finetuned_model = None

    def _format_prompt(self, inventory: List[Dict], preferences: Dict, user_request: str) -> str:
        """Format user input into ChatML template (matching training data)"""

        # Build inventory list (names only, matching training data format)
        inventory_items = [item['name'] for item in inventory]
        inventory_str = ", ".join(inventory_items)

        # Extract dietary preference (use first one if multiple, matching training data)
        preference = None
        if preferences.get("dietary_restrictions"):
            dietary_restrictions = preferences["dietary_restrictions"]
            if dietary_restrictions:
                preference = dietary_restrictions[0].lower()

        # System prompt (matching training data)
        system_prompt = "You are a recipe generation AI that creates recipes based on user inventory and preferences."

        # Build user message in training format
        if user_request:
            user_content = f"{user_request}\n\nI have {inventory_str}."
            if preference:
                user_content += f" I want a {preference} recipe."
        else:
            user_content = f"I have {inventory_str}."
            if preference:
                user_content += f" I want a {preference} recipe."

        # ChatML format (matching training data)
        prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_content}<|im_end|>
<|im_start|>assistant
"""

        return prompt

    def generate_recipe(
        self,
        inventory: List[Dict],
        preferences: Dict,
        user_request: str = "",
        use_finetuned: bool = True,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Generate a recipe using either base or fine-tuned model

        Args:
            inventory: List of available ingredients
            preferences: User preferences including dietary restrictions
            user_request: Optional natural language request
            use_finetuned: Use fine-tuned model (True) or base model (False)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter

        Returns:
            Generated recipe text
        """
        prompt = self._format_prompt(inventory, preferences, user_request)

        # Select model
        if use_finetuned and self.finetuned_model:
            model = self.finetuned_model
            model_name = "Fine-tuned"
        else:
            model = self.base_model
            model_name = "Base"

        print(f"🤖 Generating recipe with {model_name} model...")

        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(model.device)

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=False)

        # Extract only assistant's response (ChatML format)
        if "<|im_start|>assistant" in full_output:
            response = full_output.split("<|im_start|>assistant")[1]
            if "<|im_end|>" in response:
                response = response.split("<|im_end|>")[0].strip()
            else:
                response = response.strip()
            return response

        return full_output

    def generate_comparison(
        self,
        inventory: List[Dict],
        preferences: Dict,
        user_request: str = "",
        max_tokens: int = 512
    ) -> Dict[str, str]:
        """
        Generate recipes with both base and fine-tuned models for comparison

        Returns:
            Dict with "base" and "finetuned" keys containing respective recipes
        """
        base_recipe = self.generate_recipe(
            inventory, preferences, user_request,
            use_finetuned=False, max_tokens=max_tokens
        )

        finetuned_recipe = self.generate_recipe(
            inventory, preferences, user_request,
            use_finetuned=True, max_tokens=max_tokens
        )

        return {
            "base": base_recipe,
            "finetuned": finetuned_recipe
        }

    def cleanup(self):
        """Free up GPU memory"""
        del self.base_model
        if self.finetuned_model:
            del self.finetuned_model
        torch.cuda.empty_cache()
        print("✅ Models unloaded, memory freed")


# Global model instance (lazy loading)
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """Get or create global model service instance"""
    global _model_service

    if _model_service is None:
        BASE_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
        ADAPTER_PATH = "../generator"

        _model_service = ModelService(BASE_MODEL, ADAPTER_PATH)

    return _model_service
