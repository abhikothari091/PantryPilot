# model_dev/llm_eval/datasets.py

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Dict, Any

import pandas as pd

from .config import (
    RECIPES_TEST_PATH,
    RECIPES_VAL_CHAT_PATH,
    INVENTORY_PROCESSED_PATH,
)


@dataclass
class RecipeTestExample:
    """Single example from recipes_test.jsonl."""
    user_inventory: List[str]
    requested_ingredients: Optional[List[str]]
    user_request: str
    preference: Optional[str]
    cuisine: Optional[str]
    gold_output: Dict[str, Any]
    scenario: str
    generated_at: str


@dataclass
class ChatFormatExample:
    """Example from recipes_val_chat.jsonl (for prompt format reference)."""
    text: str          # full ChatML conversation
    scenario: str
    user_message: str  # plain-text user request


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_recipes_test(path: Path = RECIPES_TEST_PATH) -> List[RecipeTestExample]:
    """Load the structured test set with input/output pairs."""
    examples: List[RecipeTestExample] = []
    for row in _read_jsonl(path):
        inp = row["input"]
        out = row["output"]

        examples.append(
            RecipeTestExample(
                user_inventory=inp.get("user_inventory", []),
                requested_ingredients=inp.get("requested_ingredients"),
                user_request=inp.get("user_request") or "",
                preference=inp.get("preference"),
                cuisine=inp.get("cuisine"),
                gold_output=out,
                scenario=row.get("scenario", ""),
                generated_at=row.get("generated_at", ""),
            )
        )
    return examples


def load_recipes_val_chat(path: Path = RECIPES_VAL_CHAT_PATH) -> List[ChatFormatExample]:
    """Load the ChatML-style validation data (for prompt format reference)."""
    examples: List[ChatFormatExample] = []
    for row in _read_jsonl(path):
        examples.append(
            ChatFormatExample(
                text=row["text"],
                scenario=row.get("scenario", ""),
                user_message=row.get("user_message", ""),
            )
        )
    return examples


def load_inventory_processed(path: Path = INVENTORY_PROCESSED_PATH) -> pd.DataFrame:
    """
    Load the cleaned inventory from the data pipeline.

    Later we can sample real user inventories from this to build
    evaluation prompts that mirror the actual product.
    """
    return pd.read_csv(path)