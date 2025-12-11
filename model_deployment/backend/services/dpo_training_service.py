"""
Service for DPO Retraining.

Handles data preparation and triggers the Cloud Run Job for training.
"""
import os
import json
import subprocess
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from models import RecipePreference, User

# Cloud Run Job Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "mlops-compute-lab")
REGION = os.getenv("GCP_REGION", "us-central1")
JOB_NAME = "pantrypilot-training-job"


def get_dpo_training_data(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Fetches and formats a user's preferences into DPO training format.
    """
    preferences = db.query(RecipePreference).filter(
        RecipePreference.user_id == user_id,
        RecipePreference.skipped == False,
        RecipePreference.chosen_variant.isnot(None)
    ).order_by(RecipePreference.created_at.asc()).all()

    dpo_pairs = []
    for pref in preferences:
        if not pref.chosen_variant or not pref.rejected_variant or not pref.variant_a or not pref.variant_b:
            continue

        chosen_recipe = pref.variant_a if pref.chosen_variant == "A" else pref.variant_b
        rejected_recipe = pref.variant_b if pref.chosen_variant == "A" else pref.variant_a

        dpo_pairs.append({
            "prompt": pref.prompt,
            "chosen": chosen_recipe,
            "rejected": rejected_recipe,
        })
    
    return dpo_pairs


def trigger_cloud_run_job(user_id: int, username: str, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Triggers the Cloud Run Job for DPO training.
    
    Note: The job fetches data directly from the database, so we don't need to pass training_data.
    This function simply triggers the job execution.
    """
    if not training_data:
        message = "No training data available for this user."
        print(f"[ERROR] {message}")
        return {"status": "error", "message": message}

    try:
        print(f"[TRAINING] Triggering Cloud Run Job '{JOB_NAME}' for user {user_id} ({username}) with {len(training_data)} preference pairs.")
        
        # Execute Cloud Run Job using gcloud CLI
        cmd = [
            "gcloud", "run", "jobs", "execute", JOB_NAME,
            "--region", REGION,
            "--project", PROJECT_ID
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            message = f"Successfully triggered Cloud Run Job for user {user_id}. Job execution started."
            print(f"[GCP] {message}")
            print(f"[GCP] Output: {result.stdout}")
            return {"status": "success", "message": message, "output": result.stdout}
        else:
            message = f"Failed to trigger Cloud Run Job. Error: {result.stderr}"
            print(f"[ERROR] {message}")
            return {"status": "error", "message": message, "error": result.stderr}

    except subprocess.TimeoutExpired:
        message = "Cloud Run Job trigger timed out after 30 seconds."
        print(f"[ERROR] {message}")
        return {"status": "error", "message": message}
    except Exception as e:
        message = f"An error occurred while triggering Cloud Run Job: {e}"
        print(f"[ERROR] {message}")
        return {"status": "error", "message": str(e)}


# Alias for backward compatibility
trigger_dpo_lambda = trigger_cloud_run_job
