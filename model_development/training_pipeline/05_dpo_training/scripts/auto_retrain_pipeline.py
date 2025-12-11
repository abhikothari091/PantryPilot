import os
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# Configuration
PROJECT_ID = "mlops-compute-lab" 
REGION = "us-central1"
JOB_NAME = "pantrypilot-training-job"
CLOUD_RUN_SERVICE = "pantrypilot-llm-v2"
DB_URL = os.getenv("DATABASE_URL")

def trigger_training_job():
    """Trigger the Cloud Run Job"""
    print(f" [1/2] Triggering Cloud Run Job: {JOB_NAME}...")
    
    if not DB_URL:
        raise ValueError("DATABASE_URL env var is not set locally. Cannot pass to job.")

    # We pass the DB_URL as an override env var
    # Note: For production, use Secret Manager.
    
    cmd = [
        "gcloud", "beta", "run", "jobs", "execute", JOB_NAME,
        "--region", REGION,
        "--project", PROJECT_ID,
        "--update-env-vars", f"DATABASE_URL={DB_URL}",
        "--wait" # Wait for completion to ensure success before redeploying
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("   Job completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"   Job execution failed: {e}")
        raise

def redeploy_service():
    """Redeploy Cloud Run Service to pick up new weights"""
    print(f" [2/2] Redeploying Service {CLOUD_RUN_SERVICE}...")
    
    # We update a dummy env var to force a fresh revision
    # The container startup command handles the model download
    timestamp = subprocess.check_output(["date"]).decode().strip()
    
    cmd = [
        "gcloud", "run", "services", "update", CLOUD_RUN_SERVICE,
        "--region", REGION,
        "--project", PROJECT_ID,
        "--update-env-vars", f"LAST_MODEL_UPDATE={timestamp}"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("   Service updated.")
    except subprocess.CalledProcessError as e:
        print(f"   Service update failed: {e}")
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()
    
    print("--- Starting Remote Retraining Pipeline ---")
    
    if args.dry_run:
        print("[Dry Run] Would trigger job and redeploy service.")
        return

    try:
        # 1. Trigger Job
        trigger_training_job()
        
        # 2. Redeploy Inference Service
        redeploy_service()
        
        print("\n--- Pipeline Completed ---")
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    main()
