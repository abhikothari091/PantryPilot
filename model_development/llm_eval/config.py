# model_dev/llm_eval/config.py

from pathlib import Path

# --- Paths ---

# .../PANTRYPILOT-1/model_dev/llm_eval/config.py → parents[2] = repo root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PIPELINE_ROOT = PROJECT_ROOT / "data_pipeline"

# Where you will place the jsonl files
RECIPES_DIR = DATA_PIPELINE_ROOT / "data" / "recipes"
RECIPES_TEST_PATH = RECIPES_DIR / "recipes_test.jsonl"
RECIPES_VAL_CHAT_PATH = RECIPES_DIR / "recipes_val_chat.jsonl"

# From your existing transform scripts
INVENTORY_PROCESSED_PATH = DATA_PIPELINE_ROOT / "data" / "processed" / "inventory_cleaned.csv"

# Models
BASE_MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"
LORA_ADAPTER_DIR = PROJECT_ROOT / "models" / "llama3b_lambda_lora"

# Device preference; actual detection happens later
DEVICE_PREFERENCE = "auto"  

# --- Eval / sensitivity ---

TEMPERATURE_GRID = [0.7]
MAX_NEW_TOKENS = 320

THRESHOLDS = {
    "json_valid_rate": 0.85,
    "diet_match_rate": 0.95,
    "cuisine_match_rate": 0.90,
    "min_slice_diet_match": 0.85,
}