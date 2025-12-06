from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime
import os
import time

from database import get_db
from models import RecipeHistory, User, InventoryItem, UserProfile, RecipePreference
from routers.inventory import get_current_user
from utils.smart_inventory import find_best_inventory_match, convert_unit, parse_ingredient, normalize_unit

class GenerateRecipeRequest(BaseModel):
    user_request: str
    servings: int = 2
    compare: bool = False

class FeedbackRequest(BaseModel):
    score: int # 1=Dislike, 2=Like

class VideoGenerateRequest(BaseModel):
    prompt: str

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)


def _extract_recipe_json(recipe_content: str) -> dict:
    """
    Robustly parse model output into JSON.
    Accepts plain strings or already-parsed dicts and falls back to raw text.
    """
    if isinstance(recipe_content, dict):
        return recipe_content

    try:
        import re

        # 1. Try to find JSON inside markdown code blocks first
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', recipe_content, re.DOTALL)
        if code_block_match:
            return json.loads(code_block_match.group(1))

        # 2. Fallback: Find the first valid JSON object in the text
        start_index = recipe_content.find('{')
        if start_index != -1:
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
                    return json.loads(recipe_content[start_index:end_index+1])
                except json.JSONDecodeError:
                    json_match = re.search(r'\{.*\}', recipe_content, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group(0))
                        except json.JSONDecodeError:
                            return {"raw_text": recipe_content}
                    return {"raw_text": recipe_content}

            json_match = re.search(r'\{.*\}', recipe_content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    return {"raw_text": recipe_content}

        return {"raw_text": recipe_content}

    except Exception as e:
        print(f"JSON parsing error: {e}")
        return {"raw_text": recipe_content}

# Video generation configuration
VIDEO_GEN_ENABLED = os.getenv("VIDEO_GEN_ENABLED", "false").lower() == "true"
VIDEO_GEN_MODEL = os.getenv("VIDEO_GEN_MODEL", "veo-3.1-generate-preview")
VIDEO_GEN_API_KEY = os.getenv("VIDEO_GEN_API_KEY")
VIDEO_GEN_TIMEOUT = int(os.getenv("VIDEO_GEN_TIMEOUT", "120"))
VIDEO_GEN_POLL_SECONDS = int(os.getenv("VIDEO_GEN_POLL_SECONDS", "5"))
VIDEO_FALLBACK_URL = "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

try:
    import google.genai as genai
    from google.genai import types as genai_types
except Exception:
    genai = None
    genai_types = None

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
    if not profile:
        profile = UserProfile(user_id=current_user.id, recipe_generation_count=0)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    preferences = {
        "dietary_restrictions": profile.dietary_restrictions if profile else [],
        "allergies": profile.allergies if profile else [],
        "favorite_cuisines": profile.favorite_cuisines if profile else []
    }

    model_service = request.app.state.model_service

    next_generation_count = (profile.recipe_generation_count or 0) + 1
    is_comparison = body.compare or next_generation_count % 7 == 0

    if is_comparison:
        # Generate two variants using the same external API (fresh calls)
        variant_a_raw = model_service.generate_recipe(
            inventory_list, preferences, body.user_request, use_finetuned=True, temperature=0.7
        )
        variant_b_raw = model_service.generate_recipe(
            inventory_list, preferences, body.user_request, use_finetuned=True, temperature=0.7
        )

        variant_a = _extract_recipe_json(variant_a_raw)
        variant_b = _extract_recipe_json(variant_b_raw)

        preference_entry = RecipePreference(
            user_id=current_user.id,
            prompt=body.user_request,
            variant_a=variant_a,
            variant_b=variant_b,
            created_at=datetime.utcnow()
        )

        profile.recipe_generation_count = next_generation_count
        db.add(preference_entry)
        db.commit()
        db.refresh(preference_entry)

        return {
            "status": "success",
            "mode": "comparison",
            "generation_count": next_generation_count,
            "preference_id": preference_entry.id,
            "data": {
                "variant_a": variant_a,
                "variant_b": variant_b
            }
        }

    # Standard single recipe generation
    recipe_content = model_service.generate_recipe(
        inventory_list, preferences, body.user_request, use_finetuned=True
    )
    recipe_json = _extract_recipe_json(recipe_content)

    history_entry = RecipeHistory(
        user_id=current_user.id,
        recipe_json=recipe_json,
        user_query=body.user_request,
        servings=body.servings,
        created_at=datetime.utcnow()
    )
    profile.recipe_generation_count = next_generation_count
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    return {
        "status": "success",
        "mode": "single",
        "generation_count": next_generation_count,
        "data": {"recipe": recipe_json},
        "history_id": history_entry.id
    }

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


@router.post("/video")
def generate_recipe_video(body: VideoGenerateRequest):
    """
    Generate a recipe video. Defaults to a mock URL; when VIDEO_GEN_ENABLED is true and the
    Google GenAI client plus API key are present, attempts a live generation. Falls back to
    mock on errors to avoid breaking UX.
    """
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    video_url = VIDEO_FALLBACK_URL
    mode = "mock"

    if VIDEO_GEN_ENABLED and genai and VIDEO_GEN_API_KEY:
        try:
            client = genai.Client(api_key=VIDEO_GEN_API_KEY)
            operation = client.models.generate_videos(
                model=VIDEO_GEN_MODEL,
                prompt=prompt,
            )

            start_time = time.time()
            while not operation.done:
                if time.time() - start_time > VIDEO_GEN_TIMEOUT:
                    raise HTTPException(status_code=504, detail="Video generation timed out")
                time.sleep(max(1, VIDEO_GEN_POLL_SECONDS))
                operation = client.operations.get(operation)

            generated_video = operation.response.generated_videos[0]
            # Prefer streaming URI if available
            if hasattr(generated_video.video, "uri"):
                video_url = generated_video.video.uri
            else:
                video_url = VIDEO_FALLBACK_URL
            mode = "live"
        except HTTPException:
            raise
        except Exception as e:
            # Silent fallback keeps the front end stable
            print(f"Video generation failed, falling back to mock: {e}")
            video_url = VIDEO_FALLBACK_URL
            mode = "mock"

    return {"status": "success", "video_url": video_url, "mode": mode}

@router.post("/warmup")
def warmup_llm_service(request: Request):
    """
    Lightweight warmup endpoint to trigger external LLM service cold start.
    Called on user login to reduce latency for first recipe generation.
    Returns immediately without waiting for full generation (fire-and-forget).
    """
    import threading
    
    model_service = request.app.state.model_service
    
    # Minimal payload to wake up the Cloud Run service
    minimal_inventory = [{"name": "rice", "quantity": 1, "unit": "kg"}]
    minimal_preferences = {
        "dietary_restrictions": [],
        "cooking_style": "balanced",
        "custom_preferences": ""
    }
    
    def warmup_task():
        """Background task to trigger LLM service warmup"""
        try:
            # Fire a lightweight request with minimal tokens
            model_service.generate_recipe(
                inventory=minimal_inventory,
                preferences=minimal_preferences,
                user_request="warmup",
                max_tokens=50,  # Very short response to minimize cost
                temperature=0.7
            )
        except Exception as e:
            # Silent fail - warmup is optional, don't disrupt login
            print(f"🔥 Warmup request completed with exception (expected): {e}")
    
    # Start warmup in background thread - don't block response
    thread = threading.Thread(target=warmup_task, daemon=True)
    thread.start()
    
    return {"status": "warming", "message": "LLM service warmup initiated"}
