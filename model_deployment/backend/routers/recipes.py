from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from database import get_db
from models import RecipeHistory, User, InventoryItem, UserProfile
from routers.inventory import get_current_user
from utils.smart_inventory import find_best_inventory_match, convert_unit, parse_ingredient, normalize_unit

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

class GenerateRecipeRequest(BaseModel):
    user_request: str
    servings: int = 2
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
    # Fetch inventory and preferences (filter out depleted items)
    inventory_items = (
        db.query(InventoryItem)
        .filter(InventoryItem.user_id == current_user.id, InventoryItem.quantity > 0)
        .all()
    )
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
    # Try to parse JSON to ensure it's valid before saving
    try:
        # Improved JSON extraction logic
        import re
        
        # 1. Try to find JSON inside markdown code blocks first
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', recipe_content, re.DOTALL)
        if code_block_match:
            recipe_json = json.loads(code_block_match.group(1))
        else:
            # 2. Fallback: Find the first valid JSON object in the text
            start_index = recipe_content.find('{')
            if start_index != -1:
                # Try to find the matching closing brace by counting
                balance = 0
                end_index = -1
                in_string = False
                escape = False
                
                for i, char in enumerate(recipe_content[start_index:], start=start_index):
                    if escape:
                        escape = False
                        continue
                    
                    if char == '\\':
                        escape = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            balance += 1
                        elif char == '}':
                            balance -= 1
                            if balance == 0:
                                end_index = i
                                break
                
                if end_index != -1:
                    try:
                        recipe_json = json.loads(recipe_content[start_index:end_index+1])
                    except json.JSONDecodeError:
                        # Fallback to greedy if balanced fails (unlikely but safe)
                        json_match = re.search(r'\{.*\}', recipe_content, re.DOTALL)
                        if json_match:
                            try:
                                recipe_json = json.loads(json_match.group(0))
                            except:
                                recipe_json = {"raw_text": recipe_content}
                        else:
                            recipe_json = {"raw_text": recipe_content}
                else:
                    # No balanced brace found, try greedy
                    json_match = re.search(r'\{.*\}', recipe_content, re.DOTALL)
                    if json_match:
                        try:
                            recipe_json = json.loads(json_match.group(0))
                        except:
                            recipe_json = {"raw_text": recipe_content}
                    else:
                        recipe_json = {"raw_text": recipe_content}
            else:
                recipe_json = {"raw_text": recipe_content}
    except Exception as e:
        print(f"JSON parsing error: {e}")
        recipe_json = {"raw_text": recipe_content}

    # Save to history
    history_entry = RecipeHistory(
        user_id=current_user.id,
        recipe_json=recipe_json,
        user_query=body.user_request,
        servings=body.servings,
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
    
    if history.recipe_json:
        # Handle nested recipe structure (common in LLM output)
        recipe_data = history.recipe_json.get("recipe", history.recipe_json)

        if "main_ingredients" in recipe_data:
            # Fetch all user inventory first
            user_inventory = db.query(InventoryItem).filter(InventoryItem.user_id == current_user.id).all()
            print(f"🔍 Checking inventory for User {current_user.id}. Found {len(user_inventory)} items.")

            for ing in recipe_data["main_ingredients"]:
                ingredient_text = ing if isinstance(ing, str) else ing.get("name", "")
                if not ingredient_text:
                    continue

                req_qty, req_unit, req_name = parse_ingredient(ingredient_text)
                print(f"  Parsed Ingredient: {req_qty} {req_unit} '{req_name}'")

                match_item, score = find_best_inventory_match(user_inventory, req_name)
                if not match_item:
                    print(f"  ⚠️ No inventory match for '{req_name}'")
                    continue

                inv_unit = normalize_unit(match_item.unit)
                converted_qty = convert_unit(req_qty, req_unit, inv_unit)

                if converted_qty is not None:
                    deduction_amount = converted_qty * (history.servings if history.servings else 1)
                    old_qty = match_item.quantity
                    match_item.quantity = max(0, match_item.quantity - deduction_amount)
                    print(f"✅ MATCH ({score:.2f}) Deducted {deduction_amount:.2f} {match_item.unit} from {match_item.item_name} (Was: {old_qty}, Now: {match_item.quantity})")
                else:
                    # Unit mismatch (e.g. pcs vs lbs), fall back to simple count deduction
                    deduction_amount = history.servings if history.servings else 1
                    old_qty = match_item.quantity
                    match_item.quantity = max(0, match_item.quantity - deduction_amount)
                    print(f"⚠️ Unit mismatch ({req_unit} vs {match_item.unit}). Fallback deduction: {deduction_amount} from {match_item.item_name}")
    
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
