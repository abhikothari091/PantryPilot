"""
Configuration for DPO Training Pipeline
"""
from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
DPO_ROOT = Path(__file__).parent.parent

# Data paths
DATA_DIR = DPO_ROOT / "data"
VARIANTS_DIR = DATA_DIR / "variants"
PREFERENCE_PAIRS_DIR = DATA_DIR / "preference_pairs"
DPO_FORMATTED_DIR = DATA_DIR / "dpo_formatted"

# Model paths
TRAINED_MODELS_DIR = DPO_ROOT / "trained_models"
SFT_MODEL_PATH = PROJECT_ROOT / "model_development" / "training_pipeline" / "04_training" / "llama3b_lambda_lora"

# Config files
PERSONAS_CONFIG = DPO_ROOT / "personas.yaml"

# Evaluation paths
EVALUATION_DIR = DPO_ROOT / "evaluation"
TEST_CASES_CONFIG = EVALUATION_DIR / "test_cases.yaml"
REPORTS_DIR = EVALUATION_DIR / "reports"

# GCS paths
GCS_BUCKET = "gs://pantrypilot-dpo-models"
GCS_MODEL_PREFIX = f"{GCS_BUCKET}/v1.0"

# Model training
BASE_MODEL = "meta-llama/Llama-3.2-3B-Instruct"

# DPO hyperparameters
DPO_LEARNING_RATE = 5e-5
DPO_BETA = 0.1
DPO_EPOCHS = 3
DPO_BATCH_SIZE = 4
DPO_GRAD_ACCUMULATION = 4

# LoRA config
LORA_R = 16
LORA_ALPHA = 16
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]

# Groq API (for preference labeling)
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 1000
GROQ_TEMPERATURE = 0.0

# Vertex AI (for evaluation)
VERTEXAI_LOCATION = "us-central1"
VERTEXAI_MODEL = "gemini-2.0-flash-exp"
