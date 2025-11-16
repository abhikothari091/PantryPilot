from __future__ import annotations

import argparse
import gc
import json
import csv
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from .config import (
    PROJECT_ROOT,
    BASE_MODEL_NAME,
    LORA_ADAPTER_DIR,
    MAX_NEW_TOKENS,
)
from .datasets import RecipeTestExample
from .run_eval import build_chatml_prompt, pick_device  # reuse prompt + device logic
from .metrics import parse_model_json, compute_example_metrics, aggregate_metrics

def load_bias_dataset_json(path: Path) -> List[RecipeTestExample]:
    """Load bias dataset from a JSON array file (val_bias.json)."""
    with open(path, "r") as f:
        raw = json.load(f)

    examples: List[RecipeTestExample] = []
    for ex in raw:
        examples.append(
            RecipeTestExample(
                user_inventory=ex.get("user_inventory", []),
                requested_ingredients=[],           # placeholder for bias eval
                preference=ex.get("preference"),
                cuisine=ex.get("cuisine"),
                user_request=ex.get("user_request"),
                gold_output=None,                   # no gold labels in bias set
                scenario="bias_eval",               # mark as bias scenario
                generated_at=None,                  # not needed
            )
        )
    return examples


def generate_single(
    model,
    tokenizer,
    ex: RecipeTestExample,
    temperature: float,
    max_new_tokens: int,
    device: torch.device,
) -> str:
    """Generate raw text for a single bias example."""
    prompt = build_chatml_prompt(ex)
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

    gen_ids = out[0, enc["input_ids"].shape[-1]:]
    text = tokenizer.decode(gen_ids, skip_special_tokens=False)
    end_token = "<|im_end|>"
    if end_token in text:
        text = text.split(end_token)[0]
    return text.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bias-data",
        type=str,
        default=str(
            PROJECT_ROOT
            / "data_pipeline"
            / "data"
            / "recipes"
            / "val_bias.json"
        ),
        help="Path to small bias eval dataset (JSON array).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Generation temperature.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Optional cap on number of bias examples.",
    )
    parser.add_argument(
        "--out-csv",
        type=str,
        default=str(
            PROJECT_ROOT
            / "model_development"
            / "llm_eval"
            / "reports"
            / "bias_report.csv"
        ),
        help="Path to output CSV with slice metrics.",
    )
    args = parser.parse_args()

    device = pick_device()
    dtype = torch.float16 if device.type != "cpu" else torch.float32
    print(f"[INFO] Using device: {device}, dtype: {dtype}")

    bias_path = Path(args.bias_data)
    examples = load_bias_dataset_json(bias_path)

    if args.max_examples is not None:
        examples = examples[: args.max_examples]
    print(f"[INFO] Loaded {len(examples)} bias examples.")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)

    # slice key: (model_kind, preference or 'none', cuisine or 'none')
    slice_metrics: Dict[Tuple[str, str, str], List[Dict[str, float]]] = defaultdict(list)

    for model_kind in ["base", "lora"]:
        print(f"\n[INFO] Evaluating {model_kind} on bias set")

        if model_kind == "base":
            model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_NAME,
                torch_dtype=dtype,
            )
        else:
            base_for_lora = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_NAME,
                torch_dtype=dtype,
            )
            model = PeftModel.from_pretrained(base_for_lora, LORA_ADAPTER_DIR)

        model.to(device)
        model.eval()

        for ex in examples:
            raw = generate_single(
                model=model,
                tokenizer=tokenizer,
                ex=ex,
                temperature=args.temperature,
                max_new_tokens=MAX_NEW_TOKENS,
                device=device,
            )
            parsed, valid = parse_model_json(raw)
            m = compute_example_metrics(ex, parsed, valid)

            pref = ex.preference or "none"
            cuis = ex.cuisine or "none"
            key = (model_kind, pref, cuis)
            slice_metrics[key].append(m)

        del model
        if model_kind == "lora":
            del base_for_lora
        gc.collect()
        if device.type == "mps":
            torch.mps.empty_cache()

    # Aggregate per slice and write CSV
    reports_dir = PROJECT_ROOT / "model_development" / "llm_eval" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out_csv)

    rows = []
    for (model_kind, pref, cuis), ms in slice_metrics.items():
        n = len(ms)
        # Use the shared aggregator from metrics.py
        agg = aggregate_metrics(ms)

        row = {
        "model": model_kind,
        "preference": pref,
        "cuisine": cuis,
        "n": n,
        }
        row.update(agg)
        rows.append(row)

    if rows:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"[INFO] Bias slice report written to {out_path}")


if __name__ == "__main__":
    main()