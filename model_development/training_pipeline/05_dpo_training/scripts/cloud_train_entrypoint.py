import os
import json
import shutil
import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text
from pathlib import Path

# Configuration
# Env vars provided by Cloud Run Job
DB_URL = os.getenv("DATABASE_URL")
MODEL_VERSION = os.getenv("MODEL_VERSION", datetime.now().strftime("%Y%m%d_%H%M%S"))
GCS_MODEL_BUCKET = os.getenv("GCS_MODEL_BUCKET", "gs://pantrypilot-dpo-models")
GCS_DATA_BUCKET = os.getenv("GCS_DATA_BUCKET", "gs://pantrypilot-dvc-storage")
BASE_ADAPTER_GCS = os.getenv("BASE_ADAPTER_GCS", "gs://recipegen-llm-models/llama3b_lambda_lora")
HF_TOKEN = os.getenv("HF_TOKEN", "")
PERSONA_ID = os.getenv("PERSONA_ID", "dpo_retrained")

DATA_DIR = Path("/tmp/dpo_data")
OUTPUT_DIR = Path("/tmp/dpo_model")
ADAPTER_DIR = Path("/tmp/base_adapter")

def fetch_data_from_db():
    print(" [1/5] Fetching training data from DB...")
    
    if not DB_URL:
        # Fallback for testing if not set
        print("   Checking env for DB_URL... Not found.")
        return None, []

    engine = create_engine(DB_URL)
    query = text("""
        SELECT id, prompt, chosen_variant, rejected_variant, variant_a_raw, variant_b_raw 
        FROM recipe_preferences 
        WHERE exported_for_training IS NOT TRUE 
        AND chosen_variant IS NOT NULL
    """)

    with engine.begin() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

    if not rows:
        print("   No new data found in DB.")
        return None, []

    # Format data
    dpo_data = []
    ids = []
    skipped = 0
    for row in rows:
        # Simplified logic assuming A/B structure matches
        if row.chosen_variant == "A":
            chosen = row.variant_a_raw
            rejected = row.variant_b_raw
        else:
            chosen = row.variant_b_raw
            rejected = row.variant_a_raw
        
        # Skip records with missing or empty data (None, empty string, or whitespace)
        if not chosen or not chosen.strip():
            skipped += 1
            continue
        if not rejected or not rejected.strip():
            skipped += 1
            continue
        if not row.prompt or not row.prompt.strip():
            skipped += 1
            continue
            
        ids.append(row.id)
        dpo_data.append({"prompt": row.prompt.strip(), "chosen": chosen.strip(), "rejected": rejected.strip()})

    if skipped > 0:
        print(f"   Skipped {skipped} records with missing data.")
    
    if not dpo_data:
        print("   No valid training data after filtering.")
        return None, []

    # Save to JSONL
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    train_file = DATA_DIR / f"{PERSONA_ID}_dpo_train.jsonl"
    
    with open(train_file, 'w') as f:
        for item in dpo_data:
            f.write(json.dumps(item) + "\n")
            
    print(f"   Fetched {len(dpo_data)} valid records.")
    return train_file, ids

def get_latest_trained_model():
    """Check if there's a previously trained model in GCS_MODEL_BUCKET."""
    print("   Checking for existing trained models...")
    
    try:
        # List all versions in the model bucket
        result = subprocess.run(
            ["gcloud", "storage", "ls", GCS_MODEL_BUCKET],
            capture_output=True, text=True, check=True
        )
        
        versions = [line.strip().rstrip('/') for line in result.stdout.strip().split('\n') if line.strip()]
        
        if not versions:
            return None
        
        # Sort to get latest (versions are like gs://bucket/v20241211_123456)
        versions.sort(reverse=True)
        latest = versions[0]
        print(f"   Found latest trained model: {latest}")
        return latest
        
    except subprocess.CalledProcessError:
        print("   No existing trained models found.")
        return None

def download_base_adapter():
    """Download adapter for DPO training. Uses latest trained model if available, otherwise original."""
    print(" [2/6] Determining base adapter...")
    
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for latest trained model first (iterative training)
    latest_model = get_latest_trained_model()
    
    if latest_model:
        source = latest_model
        print(f"   Using previous training result: {source}")
    else:
        source = BASE_ADAPTER_GCS
        print(f"   No previous training found. Using original: {source}")
    
    print(f"   Downloading from {source}...")
    cmd = ["gcloud", "storage", "cp", "-r", f"{source}/*", str(ADAPTER_DIR)]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"   Adapter downloaded to {ADAPTER_DIR}")
        return ADAPTER_DIR
    except subprocess.CalledProcessError as e:
        print(f"   Failed to download adapter: {e}")
        raise

def run_training(train_file, adapter_path):
    print(" [3/6] Running DPO Training...")
    
    # We call the existing script located at:
    # /app/model_development/training_pipeline/05_dpo_training/scripts/train_dpo_persona.py
    script_path = "/app/model_development/training_pipeline/05_dpo_training/scripts/train_dpo_persona.py"
    
    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "python3", script_path,
        "--persona", PERSONA_ID,
        "--adapter", str(adapter_path),  # Use downloaded adapter
        "--data_dir", str(DATA_DIR), # Script expects {persona}_dpo_train.jsonl here
        "--output_dir", str(OUTPUT_DIR)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("   Training successful.")
        # The script creates a subdir {persona}_v1.0
        return OUTPUT_DIR / f"{PERSONA_ID}_v1.0"
    except subprocess.CalledProcessError as e:
        print(f"   Training failed: {e}")
        raise

def upload_model(model_path):
    # Version-based path: gs://pantrypilot-dpo-models/v20241211_123456/
    versioned_model_path = f"{GCS_MODEL_BUCKET}/v{MODEL_VERSION}"
    print(f" [3/5] Uploading model to {versioned_model_path}...")
    
    # Upload model
    cmd = ["gcloud", "storage", "cp", "-r", f"{model_path}/*", versioned_model_path]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"   Model uploaded to {versioned_model_path}")
    except subprocess.CalledProcessError as e:
        print(f"   Model upload failed: {e}")
        raise

def backup_training_data():
    # Save training data with version: gs://pantrypilot-dvc-storage/training_data/v20241211_123456/
    versioned_data_path = f"{GCS_DATA_BUCKET}/training_data/v{MODEL_VERSION}"
    print(f" [4/5] Backing up training data to {versioned_data_path}...")
    
    cmd = ["gcloud", "storage", "cp", "-r", f"{DATA_DIR}/*", versioned_data_path]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"   Data backed up to {versioned_data_path}")
    except subprocess.CalledProcessError as e:
        print(f"   Data backup failed: {e}")
        # Don't fail the job for data backup issues
        pass

def update_db_status(ids):
    print(" [5/6] Updating DB status...")
    engine = create_engine(DB_URL)
    
    query = text("UPDATE recipe_preferences SET exported_for_training = TRUE WHERE id IN :ids")
    with engine.begin() as conn:
        conn.execute(query, {"ids": tuple(ids)})
    print("   DB Updated.")

def main():
    print("--- Starting Cloud DPO Job ---")
    print(f"   Model Version: {MODEL_VERSION}")
    print(f"   Base Adapter: {BASE_ADAPTER_GCS}")
    print(f"   Model Output: {GCS_MODEL_BUCKET}")
    print(f"   Data Backup: {GCS_DATA_BUCKET}")
    
    # 1. Fetch data from DB
    train_file, ids = fetch_data_from_db()
    if not train_file:
        print("   Exiting job (no data).")
        return

    try:
        # 2. Download existing LoRA adapter
        adapter_path = download_base_adapter()
        
        # 3. Run DPO training
        model_path = run_training(train_file, adapter_path)
        
        # 4. Upload new model
        upload_model(model_path)
        
        # 5. Backup training data
        backup_training_data()
        
        # 6. Update DB
        if ids:
            update_db_status(ids)
        
        print(f"--- Job Completed Successfully ---")
        print(f"   Model saved to: {GCS_MODEL_BUCKET}/v{MODEL_VERSION}")
        print(f"   Data saved to: {GCS_DATA_BUCKET}/training_data/v{MODEL_VERSION}")
            
    except Exception as e:
        print(f"[FATAL] Job failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
