# model_development/llm_eval/metrics.py

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .datasets import RecipeTestExample


@dataclass
class ExampleMetrics:
    json_valid: bool
    diet_match: Optional[bool]
    cuisine_match: Optional[bool]
    inventory_coverage: Optional[float]  # 0–1 or None if no inventory


def extract_json(text: str) -> Optional[str]:
    """
    Best-effort extraction of a single JSON object from model output.

    - Strips markdown ``` fences if present.
    - Uses brace matching to find the first complete {...} block.
    """
    # Strip common markdown fences if present (```json ... ```)
    if "```" in text:
        parts = text.split("```")
        # Keep parts that contain at least one '{'
        candidates = [p for p in parts if "{" in p]
        if candidates:
            # choose the longest candidate
            text = max(candidates, key=len)

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # first complete JSON object
                return text[start : i + 1]

    # No complete brace-balanced object found
    return None


def parse_model_json(text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Return (parsed_json, is_valid)."""
    snippet = extract_json(text)
    if snippet is None:
        return None, False
    try:
        parsed = json.loads(snippet)
        return parsed, True
    except json.JSONDecodeError:
        return None, False


def compute_example_metrics(
    example: RecipeTestExample,
    generated: Dict[str, Any] | None,
    json_valid: bool,
) -> ExampleMetrics:
    """
    Compute metrics for a single example.
    `generated` is the parsed JSON (or None if invalid).
    """
    diet_match: Optional[bool] = None
    cuisine_match: Optional[bool] = None
    inventory_coverage: Optional[float] = None

    if json_valid and isinstance(generated, dict):
        recipe = generated.get("recipe", {}) if isinstance(generated.get("recipe", {}), dict) else {}
        gen_cul_pref = str(recipe.get("culinary_preference", "")).lower()
        gen_cuisine = str(recipe.get("cuisine", "")).lower()

        # Dietary preference match
        if example.preference:
            diet_match = gen_cul_pref == str(example.preference).lower()

        # Cuisine match
        if example.cuisine:
            cuisine_match = gen_cuisine == str(example.cuisine).lower()

        # Inventory coverage: fraction of inventory items mentioned in ingredients/steps
        inv = [str(x).lower() for x in example.user_inventory]
        if inv:
            ingredients = recipe.get("main_ingredients", []) or []
            steps = recipe.get("steps", "") or ""
            ing_text = " ".join(map(str, ingredients)).lower() + " " + str(steps).lower()

            hits = sum(1 for item in inv if item in ing_text)
            inventory_coverage = hits / len(inv)

    return ExampleMetrics(
        json_valid=json_valid,
        diet_match=diet_match,
        cuisine_match=cuisine_match,
        inventory_coverage=inventory_coverage,
    )


def aggregate_metrics(all_metrics: List[ExampleMetrics]) -> Dict[str, float]:
    """Aggregate over all examples into simple scalar metrics."""
    n = len(all_metrics)
    if n == 0:
        return {}

    json_valid_rate = sum(m.json_valid for m in all_metrics) / n

    diet_vals = [m.diet_match for m in all_metrics if m.diet_match is not None]
    cuisine_vals = [m.cuisine_match for m in all_metrics if m.cuisine_match is not None]
    inv_cov_vals = [
        m.inventory_coverage for m in all_metrics if m.inventory_coverage is not None
    ]

    metrics: Dict[str, float] = {
        "json_valid_rate": json_valid_rate,
    }

    if diet_vals:
        metrics["diet_match_rate"] = sum(diet_vals) / len(diet_vals)
        metrics["constraint_violation_rate"] = 1.0 - metrics["diet_match_rate"]

    if cuisine_vals:
        metrics["cuisine_match_rate"] = sum(cuisine_vals) / len(cuisine_vals)

    if inv_cov_vals:
        metrics["inventory_coverage_mean"] = sum(inv_cov_vals) / len(inv_cov_vals)

    return metrics