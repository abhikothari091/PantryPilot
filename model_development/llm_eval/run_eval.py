# model_development/llm_eval/run_eval.py

from __future__ import annotations

import argparse
import gc
import os
from typing import Dict, List
import json
from datetime import datetime
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import csv

from .config import (
    PROJECT_ROOT,
    BASE_MODEL_NAME,
    LORA_ADAPTER_DIR,
    TEMPERATURE_GRID,
    MAX_NEW_TOKENS,
)
from .datasets import load_recipes_test, RecipeTestExample
from .metrics import parse_model_json, compute_example_metrics, aggregate_metrics
import time

# Optional: allow HF token via env
HF_TOKEN = os.getenv("HF_TOKEN")
COMMON_KW = {"token": HF_TOKEN} if HF_TOKEN else {}

def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

SYSTEM_PROMPT = """
You are RecipeGen, a recipe generation AI that creates recipes based on a user's pantry inventory and preferences.

You ALWAYS respond with EXACTLY ONE JSON object and NOTHING ELSE.
- Do NOT include markdown, backticks, comments, or natural language outside the JSON.
- The JSON MUST be syntactically valid according to standard JSON (double quotes, lowercase true/false/null).

Conceptual input:
- inventory: a list of ingredient NAMES available in the pantry (no quantities).
- optional dietary_preference: e.g. "vegan", "vegetarian", "gluten-free", "dairy-free", "non-veg", or "none".
- optional cuisine: e.g. "Italian", "Chinese", "Mexican", "Indian", etc.
- optional user_request: free text such as "quick dinner", "high-protein", "comfort food", etc.

You MUST output a JSON object with this exact structure:

{
  "status": "ok",
  "missing_ingredients": [string],
  "recipe": {
    "name": string,
    "cuisine": string,
    "culinary_preference": string,
    "time": string,
    "main_ingredients": [string],
    "steps": string,
    "note": string or null
  },
  "shopping_list": [string]
}

STRICT RULES:

1. STATUS
- "status" must be "ok" unless it is truly impossible to generate a recipe.

2. MISSING_INGREDIENTS
- Only include ingredients that are NOT in the inventory but are genuinely important for the recipe.
- NEVER list more than 8 items.
- Do NOT spam variations of the same ingredient (no long lists like many meats or repeated items).
- If the recipe can be made using only the pantry inventory plus very common staples (salt, water, basic oil), set "missing_ingredients": [].

3. RECIPE
- "main_ingredients" should use items primarily from the inventory.
- "culinary_preference" MUST respect the dietary_preference if one is provided (e.g. for "vegan" you must not introduce meat, fish, eggs, or dairy).
- "cuisine" should match the requested cuisine if one is provided.
- "time" should be a short human-readable string like "20m" or "30 minutes".
- "steps" should contain around 4–8 steps, separated by "Step 1.", "Step 2.", etc., in a single string.

4. SHOPPING_LIST
- "shopping_list" should contain at most 8 items.
- It must be consistent with "missing_ingredients": usually it will be the same items or a subset.
- If "missing_ingredients" is empty, "shopping_list" must also be [].

Keep outputs concise and focused. Do NOT invent giant lists of ingredients or long, repetitive enumerations.
"""

def build_chatml_prompt(example: RecipeTestExample) -> str:
    """ChatML prompt matching our backend use case & schema."""

    parts = []

    # Inventory
    inv_str = ", ".join(example.user_inventory)
    if inv_str:
        parts.append(f"Inventory: {inv_str}.")

    # Dietary preference
    if example.preference:
        parts.append(f"Dietary preference: {example.preference}.")

    # Cuisine preference
    if example.cuisine:
        parts.append(f"Cuisine: {example.cuisine}.")

    # User request / meta request
    if example.user_request:
        parts.append(f"Request: {example.user_request}")
    else:
        parts.append("Request: Create a single recipe using my inventory.")

    user_msg = " ".join(parts)

    return (
        "<|im_start|>system\n"
        + SYSTEM_PROMPT.strip()
        + "\n<|im_end|>\n"
        + "<|im_start|>user\n"
        + user_msg
        + "\n<|im_end|>\n"
        + "<|im_start|>assistant\n"
    )

def generate_single(
    model,
    tokenizer,
    example: RecipeTestExample,
    temperature: float,
    max_new_tokens: int,
    device: torch.device,
) -> str:
    """Generate raw text for a single example."""
    prompt = build_chatml_prompt(example)
    enc = tokenizer(prompt, return_tensors="pt").to(device)

    start = time.perf_counter()
    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.perf_counter() - start
    print(f"[DEBUG] generation took {elapsed:.2f}s")

    gen_ids = out[0, enc["input_ids"].shape[-1] :]
    text = tokenizer.decode(gen_ids, skip_special_tokens=False)
    end_token = "<|im_end|>"
    if end_token in text:
        text = text.split(end_token)[0]
    return text.strip()


def eval_model(
    model,
    tokenizer,
    examples: List[RecipeTestExample],
    temperature: float,
    device: torch.device,
    max_examples: int | None = None,
) -> Dict[str, float]:
    """Evaluate a model on a subset of examples and return aggregate metrics."""
    per_example = []

    if max_examples is not None:
        examples = examples[:max_examples]

    for i, ex in enumerate(examples):
        raw = generate_single(
            model=model,
            tokenizer=tokenizer,
            example=ex,
            temperature=temperature,
            max_new_tokens=MAX_NEW_TOKENS,
            device=device,
        )

        if i == 0:
            print("=== RAW MODEL OUTPUT SAMPLE ===")
            print(raw)
            print("=== END RAW OUTPUT ===")

        parsed, valid = parse_model_json(raw)
        m = compute_example_metrics(ex, parsed, valid)
        per_example.append(m)

        print(f"[DEBUG] finished {i + 1}/{len(examples)}")

    return aggregate_metrics(per_example)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-examples",
        type=int,
        default=100,
        help="Limit number of test examples for quick runs.",
    )
    parser.add_argument(
        "--temperatures",
        type=float,
        nargs="*",
        default=TEMPERATURE_GRID,
        help="Temperatures to evaluate.",
    )
    args = parser.parse_args()

    device = pick_device()
    dtype = torch.float16 if device.type != "cpu" else torch.float32
    print(f"[INFO] Using dtype: {dtype}")
    print(f"[INFO] Using device: {device}")

    examples = load_recipes_test()
    print(f"[INFO] Loaded {len(examples)} test examples.")

    # Load tokenizer once
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, **COMMON_KW)

    results: Dict[str, Dict[str, float]] = {}

    # Load ONE model at a time to avoid MPS OOM
    for model_kind in ["base", "lora"]:
        print(f"\n[INFO] Preparing {model_kind} model")

        # Base model
        if model_kind == "base":
            model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_NAME,
        torch_dtype=dtype,
        **COMMON_KW,
        )
        else:
            base_for_lora = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_NAME,
        torch_dtype=dtype,
        **COMMON_KW,)
        
            model = PeftModel.from_pretrained(base_for_lora, LORA_ADAPTER_DIR)

        model.to(device)
        model.eval()

        for temp in args.temperatures:
            print(f"\n[INFO] Evaluating model={model_kind}, temperature={temp}")
            metrics = eval_model(
                model=model,
                tokenizer=tokenizer,
                examples=examples,
                temperature=temp,
                device=device,
                max_examples=args.max_examples,
            )
            key = f"{model_kind}_t{temp}"
            results[key] = metrics
            print("  Metrics:", metrics)

        # Free GPU / MPS memory for this model before loading the next
        del model
        if model_kind == "lora":
            del base_for_lora
        gc.collect()
        if device.type == "mps":
            torch.mps.empty_cache()

    reports_dir = PROJECT_ROOT / "model_development" / "llm_eval" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"eval_{ts}.json"

    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Also write a CSV summary
    rows = []
    for run_name, mets in results.items():
        model_kind, temp_str = run_name.split("_t")
        row = {
         "model": model_kind,
         "temperature": float(temp_str),
        }
        row.update(mets)
        rows.append(row)

    csv_path = reports_dir / f"eval_summary_{ts}.csv"
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"[INFO] Saved metrics JSON to {json_path}")
    print(f"[INFO] Saved metrics CSV to {csv_path}")

    print("\n=== Summary ===")
    for run_name, mets in results.items():
        print(run_name, "→", mets)


if __name__ == "__main__":
    main()