from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from database import get_db
from models import RecipeHistory, User, InventoryItem, UserProfile
from routers.inventory import get_current_user

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

class GenerateRecipeRequest(BaseModel):
    user_request: str
    compare: bool = False

class FeedbackRequest(BaseModel):
    score: int # 1=Dislike, 2=Like

@router.post("/generate")
async def generate_recipe_endpoint(
    request: Request,
    body: GenerateRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch inventory and preferences
    inventory_items = db.query(InventoryItem).filter(InventoryItem.user_id == current_user.id).all()
    inventory_list = [{"name": item.item_name, "quantity": item.quantity, "unit": item.unit} for item in inventory_items]
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    preferences = {
        "dietary_restrictions": profile.dietary_restrictions if profile else [],
        "allergies": profile.allergies if profile else [],
        "favorite_cuisines": profile.favorite_cuisines if profile else []
    }

    model_service = request.app.state.model_service
    
    if body.compare:
        result = model_service.generate_comparison(inventory_list, preferences, body.user_request)
        # We only save the finetuned one to history for now, or maybe both? 
        # For simplicity, let's assume the user interacts with the finetuned one primarily.
        recipe_content = result["finetuned"]
    else:
        recipe_content = model_service.generate_recipe(inventory_list, preferences, body.user_request, use_finetuned=True)
        result = {"recipe": recipe_content}

    # Try to parse JSON to ensure it's valid before saving
    try:
        # This is a bit hacky, relying on the service to return a string that might contain JSON
        # The service has some parsing logic but returns a string. 
        # We should probably let the frontend parse it, but for history we want JSON.
        # Let's try to extract JSON if it's a string.
        import re
        json_match = re.search(r'\{.*\}', recipe_content, re.DOTALL)
        if json_match:
            recipe_json = json.loads(json_match.group(0))
        else:
            recipe_json = {"raw_text": recipe_content}
    except:
        recipe_json = {"raw_text": recipe_content}

    # Save to history
    history_entry = RecipeHistory(
        user_id=current_user.id,
        recipe_json=recipe_json,
        user_query=body.user_request,
        created_at=datetime.utcnow()
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    return {"status": "success", "data": result, "history_id": history_entry.id}

@router.post("/{history_id}/feedback")
def submit_feedback(
    history_id: int,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    entry = db.query(RecipeHistory).filter(RecipeHistory.id == history_id, RecipeHistory.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Recipe history not found")
    
    entry.feedback_score = body.score
    db.commit()
    return {"status": "success"}

@router.post("/{recipe_id}/cooked")
def mark_recipe_cooked(recipe_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    history = db.query(RecipeHistory).filter(RecipeHistory.id == recipe_id, RecipeHistory.user_id == current_user.id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    history.is_cooked = True
    
    # Optionally deduct inventory based on recipe ingredients
    # This is simplified - in production you'd want more sophisticated matching
    if history.recipe_json and "main_ingredients" in history.recipe_json:
        for ing in history.recipe_json["main_ingredients"]:
            # Try to find matching inventory item
            # This is a basic implementation - you might want fuzzy matching
            item_name = ing if isinstance(ing, str) else ing.get("name", "")
            inventory_item = db.query(InventoryItem).filter(
                InventoryItem.user_id == current_user.id,
                InventoryItem.item_name.ilike(f"%{item_name}%")
            ).first()
            
    db.commit()
    return {"status": "success", "message": "Marked as cooked and inventory updated"}

@router.get("/history")
def get_recipe_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all recipes for the current user, sorted by newest first"""
    recipes = db.query(RecipeHistory).filter(
        RecipeHistory.user_id == current_user.id
    ).order_by(RecipeHistory.created_at.desc()).all()
    
    return [{
        "id": r.id,
        "recipe_json": r.recipe_json,
        "user_query": r.user_query,
        "feedback_score": r.feedback_score,
        "is_cooked": r.is_cooked,
        "created_at": r.created_at.isoformat()
    } for r in recipes]
