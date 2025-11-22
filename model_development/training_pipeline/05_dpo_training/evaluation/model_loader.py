"""
Model Loader for DPO Evaluation

Loads SFT baseline model and DPO persona models for comparison.
Supports efficient loading and inference with LoRA adapters.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gc


class RecipeModelLoader:
    """
    Load and manage SFT and DPO models for evaluation
    """

    def __init__(
        self,
        base_model_id: str = "meta-llama/Llama-3.2-3B-Instruct",
        sft_adapter_path: Optional[str] = None,
        dpo_models_dir: Optional[str] = None,
        device_map: str = "auto",
        torch_dtype = torch.float16
    ):
        """
        Initialize model loader

        Args:
            base_model_id: Base model from HuggingFace
            sft_adapter_path: Path to SFT LoRA adapter
            dpo_models_dir: Directory containing DPO persona models
            device_map: Device placement strategy
            torch_dtype: Model dtype (float16 for efficiency)
        """
        self.base_model_id = base_model_id
        self.sft_adapter_path = Path(sft_adapter_path) if sft_adapter_path else None
        self.dpo_models_dir = Path(dpo_models_dir) if dpo_models_dir else None
        self.device_map = device_map
        self.torch_dtype = torch_dtype

        # Loaded models cache
        self.tokenizer = None
        self.base_model = None
        self.sft_model = None
        self.dpo_models = {}

        print(f"📦 Model Loader initialized")
        print(f"   Base: {base_model_id}")
        print(f"   SFT adapter: {sft_adapter_path}")
        print(f"   DPO models: {dpo_models_dir}")

    def load_tokenizer(self):
        """Load tokenizer (shared across all models)"""
        if self.tokenizer is None:
            print(f"\n🔤 Loading tokenizer from {self.base_model_id}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_id)

            # Ensure pad token is set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            print(f"   ✅ Tokenizer loaded (vocab size: {len(self.tokenizer)})")

        return self.tokenizer

    def load_base_model(self):
        """Load base model (without any adapters)"""
        if self.base_model is None:
            print(f"\n🤖 Loading base model: {self.base_model_id}...")
            self.base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_id,
                torch_dtype=self.torch_dtype,
                device_map=self.device_map,
                low_cpu_mem_usage=True
            )
            self.base_model.eval()
            print(f"   ✅ Base model loaded")
            print(f"   Device: {next(self.base_model.parameters()).device}")
            print(f"   Dtype: {next(self.base_model.parameters()).dtype}")

        return self.base_model

    def load_sft_model(self, force_reload: bool = False):
        """
        Load SFT model (base + LoRA adapter)

        Args:
            force_reload: Reload even if already loaded

        Returns:
            SFT model with LoRA adapter
        """
        if self.sft_model is not None and not force_reload:
            return self.sft_model

        if self.sft_adapter_path is None:
            raise ValueError("SFT adapter path not provided")

        if not self.sft_adapter_path.exists():
            raise FileNotFoundError(f"SFT adapter not found: {self.sft_adapter_path}")

        print(f"\n🎯 Loading SFT model...")
        print(f"   Adapter: {self.sft_adapter_path}")

        # Load base model first
        base = self.load_base_model()

        # Load LoRA adapter
        self.sft_model = PeftModel.from_pretrained(base, str(self.sft_adapter_path))
        self.sft_model.eval()

        print(f"   ✅ SFT model loaded")

        return self.sft_model

    def load_dpo_model(self, persona_id: str, force_reload: bool = False):
        """
        Load DPO persona model

        Args:
            persona_id: Persona identifier (e.g., "persona_a_korean_spicy")
            force_reload: Reload even if already loaded

        Returns:
            DPO persona model
        """
        if persona_id in self.dpo_models and not force_reload:
            return self.dpo_models[persona_id]

        if self.dpo_models_dir is None:
            raise ValueError("DPO models directory not provided")

        # Find persona model directory
        persona_dirs = list(self.dpo_models_dir.glob(f"{persona_id}*"))
        if not persona_dirs:
            raise FileNotFoundError(f"DPO model not found for: {persona_id}")

        dpo_path = persona_dirs[0]
        print(f"\n🎭 Loading DPO model: {persona_id}")
        print(f"   Path: {dpo_path}")

        # Load base model first
        base = self.load_base_model()

        # Load DPO adapter
        dpo_model = PeftModel.from_pretrained(base, str(dpo_path))
        dpo_model.eval()

        self.dpo_models[persona_id] = dpo_model
        print(f"   ✅ DPO model loaded")

        return dpo_model

    def unload_model(self, model_type: str):
        """
        Unload a model to free memory

        Args:
            model_type: "sft" or persona_id for DPO models
        """
        if model_type == "sft" and self.sft_model is not None:
            del self.sft_model
            self.sft_model = None
            print(f"   🗑️  Unloaded SFT model")
        elif model_type in self.dpo_models:
            del self.dpo_models[model_type]
            print(f"   🗑️  Unloaded DPO model: {model_type}")

        # Force garbage collection
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def generate_recipe(
        self,
        model,
        inventory: List[str],
        user_request: str,
        persona_config: Optional[Dict] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        """
        Generate recipe with a model

        Args:
            model: The model to use (SFT or DPO)
            inventory: List of available ingredients
            user_request: User's request
            persona_config: Optional persona configuration for system prompt
            max_new_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated recipe (JSON string)
        """
        # Ensure tokenizer is loaded
        if self.tokenizer is None:
            self.load_tokenizer()

        # Build prompt
        prompt = self._build_prompt(inventory, user_request, persona_config)

        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(model.device)

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=False)

        # Extract assistant response
        recipe_output = self._extract_assistant_response(full_output)

        return recipe_output

    def _build_prompt(
        self,
        inventory: List[str],
        user_request: str,
        persona_config: Optional[Dict] = None
    ) -> str:
        """
        Build ChatML format prompt

        Args:
            inventory: Available ingredients
            user_request: User's request
            persona_config: Optional persona configuration

        Returns:
            Formatted prompt string
        """
        # System message
        if persona_config:
            # DPO persona-specific system prompt
            cuisines = ", ".join(persona_config.get("preferences", {}).get("cuisine", []))
            flavors = ", ".join(persona_config.get("preferences", {}).get("flavor_profile", []))
            preferences = ", ".join(persona_config.get("preference_keywords", []))

            system_content = f"""You are a recipe generation AI specializing in {cuisines} cuisine.
You prefer {flavors} flavors and {persona_config.get('preferences', {}).get('cooking_style', 'any')} cooking style.
Try to incorporate ingredients like: {preferences}.
Generate recipes in valid JSON format matching the exact structure you were trained on."""
        else:
            # Generic SFT system prompt
            system_content = "You are a helpful recipe generation AI. Generate recipes in valid JSON format based on the user's available ingredients and preferences."

        # User message
        user_content = f"""Generate a recipe using these available ingredients: {', '.join(inventory)}

User request: {user_request}

Generate a complete recipe in JSON format."""

        # ChatML format (Llama 3.2 style)
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_content}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user_content}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        return prompt

    def _extract_assistant_response(self, full_output: str) -> str:
        """
        Extract assistant's response from full output

        Args:
            full_output: Full model output with special tokens

        Returns:
            Cleaned assistant response
        """
        # Find assistant response
        if "<|start_header_id|>assistant<|end_header_id|>" in full_output:
            # Split and get assistant part
            parts = full_output.split("<|start_header_id|>assistant<|end_header_id|>")
            if len(parts) > 1:
                assistant_part = parts[1]

                # Remove end tokens
                if "<|eot_id|>" in assistant_part:
                    assistant_part = assistant_part.split("<|eot_id|>")[0]

                # Clean up
                response = assistant_part.strip()

                # Extract JSON if embedded in text
                if "```json" in response:
                    # Find JSON block
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    if json_end > json_start:
                        response = response[json_start:json_end].strip()
                elif "{" in response and "}" in response:
                    # Extract JSON object
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    response = response[json_start:json_end]

                return response

        # Fallback: return as-is
        return full_output.strip()

    def get_memory_usage(self) -> Dict:
        """Get current GPU memory usage"""
        if torch.cuda.is_available():
            return {
                "allocated_gb": torch.cuda.memory_allocated() / 1e9,
                "reserved_gb": torch.cuda.memory_reserved() / 1e9,
                "max_allocated_gb": torch.cuda.max_memory_allocated() / 1e9
            }
        return {"message": "CUDA not available"}


class SequentialModelLoader(RecipeModelLoader):
    """
    Load models sequentially to save memory

    Loads one model at a time, unloading previous model before loading next.
    Useful for evaluating multiple personas with limited GPU memory.
    """

    def generate_sft_recipe(self, inventory: List[str], user_request: str, **kwargs) -> str:
        """Generate recipe with SFT model, then unload"""
        model = self.load_sft_model()
        recipe = self.generate_recipe(model, inventory, user_request, **kwargs)
        return recipe

    def generate_dpo_recipe(
        self,
        persona_id: str,
        persona_config: Dict,
        inventory: List[str],
        user_request: str,
        **kwargs
    ) -> str:
        """Generate recipe with DPO model, then optionally unload"""
        model = self.load_dpo_model(persona_id)
        recipe = self.generate_recipe(
            model,
            inventory,
            user_request,
            persona_config=persona_config,
            **kwargs
        )
        return recipe

    def compare_models(
        self,
        persona_id: str,
        persona_config: Dict,
        inventory: List[str],
        user_request: str,
        **kwargs
    ) -> Tuple[str, str]:
        """
        Generate recipes with both SFT and DPO, managing memory efficiently

        Returns:
            (sft_recipe, dpo_recipe)
        """
        # Generate with SFT
        print(f"   📝 Generating with SFT model...")
        sft_recipe = self.generate_sft_recipe(inventory, user_request, **kwargs)

        # Generate with DPO
        print(f"   📝 Generating with DPO model ({persona_id})...")
        dpo_recipe = self.generate_dpo_recipe(
            persona_id,
            persona_config,
            inventory,
            user_request,
            **kwargs
        )

        return sft_recipe, dpo_recipe


if __name__ == "__main__":
    # Test the model loader
    import yaml

    # Paths
    project_root = Path(__file__).parent.parent
    sft_path = project_root / "models/llama3b_lambda_lora"
    dpo_path = project_root / "models/dpo_personas"
    personas_file = project_root / "data_pipeline/05_dpo_training/personas.yaml"

    # Load personas
    with open(personas_file) as f:
        personas = yaml.safe_load(f)['personas']

    # Initialize loader
    loader = SequentialModelLoader(
        base_model_id="meta-llama/Llama-3.2-3B-Instruct",
        sft_adapter_path=str(sft_path),
        dpo_models_dir=str(dpo_path)
    )

    # Load tokenizer
    loader.load_tokenizer()

    # Test generation
    test_inventory = ["chicken", "rice", "gochujang", "garlic", "scallions"]
    test_request = "Make me a spicy Korean recipe"

    print("\n" + "="*60)
    print("Testing SFT vs DPO generation")
    print("="*60)

    sft_recipe, dpo_recipe = loader.compare_models(
        persona_id="persona_a_korean_spicy",
        persona_config=personas["persona_a_korean_spicy"],
        inventory=test_inventory,
        user_request=test_request,
        max_new_tokens=512,
        temperature=0.7
    )

    print("\n📊 SFT Recipe:")
    print(sft_recipe[:200] + "..." if len(sft_recipe) > 200 else sft_recipe)

    print("\n📊 DPO Recipe:")
    print(dpo_recipe[:200] + "..." if len(dpo_recipe) > 200 else dpo_recipe)

    print("\n✅ Model loader test complete")
