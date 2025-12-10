"""
Training service helpers for triggering DPO retraining jobs and tracking status.
"""

import logging
from datetime import datetime
from typing import Dict


def trigger_dpo_training(user_id: int, username: str) -> Dict[str, str]:
    """
    Stub implementation that will later be replaced with the real Neon -> Lambda flow.
    Logs the intent to start training and returns a mock job payload.
    """
    job_id = f"dpo-training-{user_id}-{int(datetime.utcnow().timestamp())}"
    logging.info(
        "[TRAINING] Starting sample retraining job for user %s (ID=%s)",
        username,
        user_id
    )

    return {
        "id": job_id,
        "status": "training_started",
        "user_id": user_id,
        "started_at": datetime.utcnow().isoformat()
    }
