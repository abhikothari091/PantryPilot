"""
Training Router - Handles retraining approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from database import get_db
from dependencies import get_current_user
from models import User, UserProfile, RecipePreference

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/pending")
def get_pending_retraining_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get users who have reached the preference threshold (50+).
    Admin endpoint to see who is eligible for retraining.
    """
    # Check if admin
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all users with 50+ preferences
    threshold = 50
    
    # Query users with their preference counts
    from sqlalchemy import func
    
    results = db.query(
        RecipePreference.user_id,
        func.count(RecipePreference.id).label('count')
    ).filter(
        RecipePreference.skipped == False  # Only count actual choices
    ).group_by(
        RecipePreference.user_id
    ).having(
        func.count(RecipePreference.id) >= threshold
    ).all()
    
    pending_users = []
    for user_id, count in results:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            pending_users.append({
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
                "preference_count": count,
                "status": "pending"
            })
    
    return {
        "threshold": threshold,
        "pending_count": len(pending_users),
        "users": pending_users
    }


@router.post("/approve/{user_id}")
def approve_retraining(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve retraining for a specific user.
    This endpoint is called when admin clicks the approval link in Slack.
    
    Note: This doesn't automatically trigger training - it logs the approval
    for manual training execution on Lambda Labs.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get preference count
    preference_count = db.query(RecipePreference).filter(
        RecipePreference.user_id == user_id,
        RecipePreference.skipped == False
    ).count()
    
    if preference_count < 50:
        raise HTTPException(
            status_code=400, 
            detail=f"User has only {preference_count} preferences. Minimum 50 required."
        )
    
    # Log approval (in production, this would update a RetrainingRequest table)
    approval_log = {
        "user_id": user_id,
        "username": user.username,
        "preference_count": preference_count,
        "approved_at": datetime.utcnow().isoformat(),
        "status": "approved",
        "message": f"Retraining approved for user {user.username}. "
                   f"Export preferences and run DPO training on Lambda Labs."
    }
    
    print(f"[TRAINING] Approved retraining for user {user.username} (ID: {user_id})")
    print(f"[TRAINING] Preference count: {preference_count}")
    print(f"[TRAINING] Run: python train_dpo_persona.py --user_id {user_id}")
    
    return approval_log


@router.get("/export/{user_id}")
def export_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a user's preferences in DPO training format.
    Admin endpoint for preparing training data.
    """
    # Check if admin
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get preferences
    preferences = db.query(RecipePreference).filter(
        RecipePreference.user_id == user_id,
        RecipePreference.skipped == False
    ).all()
    
    # Format for DPO training
    dpo_pairs = []
    for pref in preferences:
        if pref.chosen_variant and pref.rejected_variant:
            dpo_pairs.append({
                "prompt": pref.prompt,
                "chosen": pref.chosen_variant,
                "rejected": pref.rejected_variant,
                "generation_number": pref.generation_number,
                "created_at": pref.created_at.isoformat() if pref.created_at else None
            })
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_preferences": len(dpo_pairs),
        "dpo_pairs": dpo_pairs
    }
