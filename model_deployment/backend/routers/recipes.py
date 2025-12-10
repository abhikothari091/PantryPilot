from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime
import os
import time
import base64

from database import get_db
from models import RecipeHistory, User, InventoryItem, UserProfile, RecipePreference
from routers.inventory import get_current_user
from utils.smart_inventory import find_best_inventory_match, convert_unit, parse_ingredient, normalize_unit

class GenerateRecipeRequest(BaseModel):
    user_request: str
    servings: int = 2
    compare: bool = False

class PreferenceChoiceRequest(BaseModel):
    chosen_variant: str  # "A" or "B"
    servings: int = 2

class PreferenceSkipRequest(BaseModel):
    reason: Optional[str] = None

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


def _sanitize_recipe(recipe_json: dict) -> dict:
    """
    Remove clearly unused/ignored ingredients from main_ingredients.
    Acts in-place on the provided dict.
    """
    if not isinstance(recipe_json, dict):
        return recipe_json

    recipe_node = recipe_json.get("recipe", recipe_json)
    ingredients = recipe_node.get("main_ingredients")
    if isinstance(ingredients, list):
        cleaned = []
        for ing in ingredients:
            text = ""
            if isinstance(ing, str):
                text = ing
            elif isinstance(ing, dict):
                text = ing.get("name") or ing.get("ingredient") or ""
            else:
                cleaned.append(ing)
                continue

            lowered = text.lower()
            if "not used" in lowered or "ignore" in lowered:
                continue
            cleaned.append(ing)

        recipe_node["main_ingredients"] = cleaned

    return recipe_json

# Video generation configuration
VIDEO_GEN_ENABLED = os.getenv("VIDEO_GEN_ENABLED", "false").lower() == "true"
# Additional guard: require explicit opt-in for live video generation
VIDEO_GEN_ALLOW_LIVE = os.getenv("VIDEO_GEN_ALLOW_LIVE", "false").lower() == "true"
VIDEO_GEN_MODEL = os.getenv("VIDEO_GEN_MODEL", "veo-3.1-generate-preview")
VIDEO_GEN_API_KEY = os.getenv("VIDEO_GEN_API_KEY")
VIDEO_GEN_TIMEOUT = int(os.getenv("VIDEO_GEN_TIMEOUT", "180"))  # Increased for production
VIDEO_GEN_POLL_SECONDS = int(os.getenv("VIDEO_GEN_POLL_SECONDS", "10"))  # Match official docs
VIDEO_FALLBACK_URL = "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

# Import Google GenAI following official documentation pattern
genai = None
try:
    from google import genai as google_genai
    genai = google_genai
except ImportError:
    pass

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

        variant_a = _sanitize_recipe(_extract_recipe_json(variant_a_raw))
        variant_b = _sanitize_recipe(_extract_recipe_json(variant_b_raw))

        preference_entry = RecipePreference(
            user_id=current_user.id,
            prompt=body.user_request,
            user_query=body.user_request,
            servings=body.servings,
            generation_number=next_generation_count,
            variant_a=variant_a,
            variant_b=variant_b,
            variant_a_raw=variant_a_raw if isinstance(variant_a_raw, str) else json.dumps(variant_a_raw),
            variant_b_raw=variant_b_raw if isinstance(variant_b_raw, str) else json.dumps(variant_b_raw),
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
    recipe_json = _sanitize_recipe(_extract_recipe_json(recipe_content))

    history_entry = RecipeHistory(
        user_id=current_user.id,
        recipe_json=recipe_json,
        raw_response=recipe_content if isinstance(recipe_content, str) else json.dumps(recipe_content),
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


@router.post("/preference/{preference_id}/choose")
def choose_preference(
    preference_id: int,
    body: PreferenceChoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    choice = body.chosen_variant.upper()
    if choice not in ("A", "B"):
        raise HTTPException(status_code=400, detail="chosen_variant must be 'A' or 'B'")

    pref = db.query(RecipePreference).filter(
        RecipePreference.id == preference_id,
        RecipePreference.user_id == current_user.id
    ).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    chosen_json = pref.variant_a if choice == "A" else pref.variant_b
    rejected = "B" if choice == "A" else "A"

    history_entry = RecipeHistory(
        user_id=current_user.id,
        recipe_json=chosen_json,
        user_query=pref.prompt or pref.user_query or "",
        servings=body.servings,
        created_at=datetime.utcnow()
    )
    pref.chosen_variant = choice
    pref.rejected_variant = rejected
    pref.chosen_at = datetime.utcnow()
    pref.updated_at = datetime.utcnow()
    pref.chosen_recipe_history_id = None

    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    pref.chosen_recipe_history_id = history_entry.id
    db.commit()

    # Check if user has reached preference threshold for retraining notification
    total_preferences = db.query(RecipePreference).filter(
        RecipePreference.user_id == current_user.id,
        RecipePreference.skipped == False,
        RecipePreference.chosen_variant != None
    ).count()

    total_with_feedback = db.query(RecipeHistory).filter(
        RecipeHistory.user_id == current_user.id,
        RecipeHistory.feedback_score > 0
    ).count()

    liked_count = db.query(RecipeHistory).filter(
        RecipeHistory.user_id == current_user.id,
        RecipeHistory.feedback_score == 2
    ).count()

    satisfaction_ratio = liked_count / total_with_feedback if total_with_feedback > 0 else 1.0
    
    # Send notification if threshold reached (50 preferences)
    from services.notification_service import check_and_notify_threshold
    import os
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    check_and_notify_threshold(
        user_id=current_user.id,
        username=current_user.username,
        preference_count=total_preferences,
        satisfaction_ratio=satisfaction_ratio,
        feedback_count=total_with_feedback,
        db=db,
        base_url=base_url
    )

    return {
        "status": "success",
        "preference_id": preference_id,
        "chosen_variant": choice,
        "history_id": history_entry.id
    }


@router.post("/preference/{preference_id}/skip")
def skip_preference(
    preference_id: int,
    body: PreferenceSkipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pref = db.query(RecipePreference).filter(
        RecipePreference.id == preference_id,
        RecipePreference.user_id == current_user.id
    ).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")

    pref.skipped = True
    pref.updated_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "preference_id": preference_id, "skipped": True}

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
    Generate a recipe video using Google Veo 3.1 API.
    
    When VIDEO_GEN_ENABLED and VIDEO_GEN_ALLOW_LIVE are true and API key is configured,
    attempts live generation. Falls back to mock video URL on errors to maintain stable UX.
    
    Reference: https://ai.google.dev/gemini-api/docs/video
    """
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    video_url = VIDEO_FALLBACK_URL
    mode = "mock"

    # Rich, guided prompt to encourage stepwise cooking visuals
    detailed_prompt = (
        "Create a 20-second cooking video for the dish below. "
        "Show clear, sequential steps (Step 1, Step 2, Step 3) with close-ups of ingredients, pan actions, "
        "and a final plated hero shot. Natural lighting, no text overlays, no voiceover. "
        "Keep pacing brisk and visually coherent.\n\n"
        f"Dish details: {prompt}"
    )

    # Require explicit allow flag to enable live generation
    if VIDEO_GEN_ENABLED and VIDEO_GEN_ALLOW_LIVE and genai and VIDEO_GEN_API_KEY:
        try:
            print(f"🎬 Starting video generation with model: {VIDEO_GEN_MODEL}")
            print(f"📝 Prompt: {detailed_prompt[:200]}...")
            
            # Initialize client following official documentation
            client = genai.Client(api_key=VIDEO_GEN_API_KEY)
            
            # Start video generation (async operation)
            operation = client.models.generate_videos(
                model=VIDEO_GEN_MODEL,
                prompt=detailed_prompt,
            )
            print(f"📊 Operation started: {operation.name if hasattr(operation, 'name') else 'unknown'}")

            # Poll until video is ready (following official docs pattern)
            start_time = time.time()
            poll_count = 0
            while not operation.done:
                elapsed = time.time() - start_time
                if elapsed > VIDEO_GEN_TIMEOUT:
                    print(f"⏰ Video generation timed out after {elapsed:.0f}s")
                    raise HTTPException(status_code=504, detail="Video generation timed out")
                
                poll_count += 1
                print(f"⏳ Waiting for video... (poll #{poll_count}, {elapsed:.0f}s elapsed)")
                time.sleep(VIDEO_GEN_POLL_SECONDS)
                
                # Refresh operation status (per official docs)
                operation = client.operations.get(operation)

            # Extract video URL from completed operation
            if operation.response and operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]
                video_obj = getattr(generated_video, "video", None)
                mime_type = "video/mp4"
                if video_obj and getattr(video_obj, "mime_type", None):
                    mime_type = video_obj.mime_type

                if video_obj:
                    try:
                        # Download the bytes using the official helper and embed as data URL for reliable playback
                        video_bytes = client.files.download(file=video_obj)
                        b64 = base64.b64encode(video_bytes).decode("ascii")
                        video_url = f"data:{mime_type};base64,{b64}"
                        mode = "live"
                        print(f"✅ Video generated successfully ({mime_type}), size={len(video_bytes)} bytes")
                    except Exception as download_exc:
                        print(f"⚠️ Video download failed: {type(download_exc).__name__}: {download_exc}")
                        # Fallback to raw URI if provided
                        if getattr(video_obj, "uri", None):
                            video_url = video_obj.uri
                            mode = "live"
                            print("ℹ️ Using video URI directly.")
                        else:
                            print("⚠️ No usable video URI; using fallback.")
            else:
                print("⚠️ No video in response, using fallback")
                
        except HTTPException:
            raise
        except Exception as e:
            # Silent fallback keeps the front end stable
            print(f"❌ Video generation failed: {type(e).__name__}: {e}")
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
