"""
Training Router - Handles retraining approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from dependencies import get_current_user
from models import User, RecipePreference
from services import dpo_training_service

router = APIRouter(prefix="/training", tags=["training"])

MIN_PREFERENCES_FOR_TRAINING = 50

@router.get("/pending")
def get_pending_retraining_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get users who have reached the preference threshold.
    Admin endpoint to see who is eligible for retraining.
    """
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from sqlalchemy import func
    
    results = db.query(
        RecipePreference.user_id,
        func.count(RecipePreference.id).label('count')
    ).filter(
        RecipePreference.skipped == False,
        RecipePreference.chosen_variant.isnot(None)
    ).group_by(
        RecipePreference.user_id
    ).having(
        func.count(RecipePreference.id) >= MIN_PREFERENCES_FOR_TRAINING
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
        "threshold": MIN_PREFERENCES_FOR_TRAINING,
        "pending_count": len(pending_users),
        "users": pending_users
    }


@router.get("/approve/{user_id}", response_class=HTMLResponse)
def approve_retraining(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve and trigger DPO retraining for a specific user.
    This endpoint is called when an admin clicks the approval link in Slack.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(content="<h1>Error: User not found</h1>", status_code=404)

    # 1. Fetch and format data using the service
    training_data = dpo_training_service.get_dpo_training_data(db, user_id)
    
    if len(training_data) < MIN_PREFERENCES_FOR_TRAINING:
        return HTMLResponse(
            content=f"<h1>Error: Not enough data</h1><p>User {user.username} has only {len(training_data)} preferences. Minimum {MIN_PREFERENCES_FOR_TRAINING} required.</p>",
            status_code=400
        )

    # 2. Trigger the Lambda function
    result = dpo_training_service.trigger_dpo_lambda(user.id, user.username, training_data)

    if result["status"] == "success":
        return HTMLResponse(content=f"<h1>Retraining Initiated</h1><p>DPO retraining for user <b>{user.username}</b> (ID: {user.id}) has been successfully triggered.</p><p>Preference pairs sent: {len(training_data)}</p>")
    else:
        return HTMLResponse(content=f"<h1>Error</h1><p>Failed to trigger retraining for user {user.username}.</p><p>Reason: {result['message']}</p>", status_code=500)


@router.get("/export/{user_id}")
def export_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a user's preferences in DPO training format using the centralized service.
    Admin endpoint for preparing training data.
    """
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use the centralized service to get data
    dpo_pairs = dpo_training_service.get_dpo_training_data(db, user_id)
    
    return {
        "user_id": user_id,
        "username": user.username,
        "total_preferences": len(dpo_pairs),
        "dpo_pairs": dpo_pairs
    }
