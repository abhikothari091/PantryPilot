"""
PantryPilot Recipe Generator API
FastAPI backend with MLX model inference
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import uvicorn
from pathlib import Path
import json
import re
from datetime import datetime

from model_service import ModelService
from database import Database

app = FastAPI(title="PantryPilot Recipe Generator")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
model_service: Optional[ModelService] = None
db: Optional[Database] = None

# Request/Response models
class InventoryItem(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None

class UserPreferences(BaseModel):
    dietary_restrictions: List[str] = []
    cooking_style: str = "balanced"
    custom_preferences: str = ""

class GenerateRecipeRequest(BaseModel):
    user_request: str  # Natural language request (e.g., "I want something healthy for dinner")
    compare: bool = False
    inventory: List[InventoryItem] = []
    preferences: UserPreferences = UserPreferences()

class RecipeDetails(BaseModel):
    name: str
    cuisine: str
    culinary_preference: str
    time: str
    main_ingredients: List[str]
    steps: str
    note: Optional[str] = None

class RecipeOutput(BaseModel):
    status: str
    missing_ingredients: List[str]
    recipe: RecipeDetails
    shopping_list: List[Dict[str, Any]]

class RecipeResponse(BaseModel):
    recipe: RecipeOutput
    base_recipe: Optional[RecipeOutput] = None  # Only if compare=True

class RewardRequest(BaseModel):
    chosen_recipe: RecipeDetails
    rejected_recipe: RecipeDetails
    user_request: str

@app.on_event("startup")
async def startup_event():
    """Initialize model and database on server start"""
    global model_service, db

    print("🚀 Initializing RecipeGen-LLM API...")

    # Load Llama 3B model with Lambda-trained LoRA adapter
    model_path = "meta-llama/Llama-3.2-3B-Instruct"
    adapter_path = Path(__file__).parent.parent / "models" / "llama3b_lambda_lora"

    print(f"📍 Base model: {model_path}")
    print(f"📍 LoRA adapter: {adapter_path}")
    model_service = ModelService(model_path, str(adapter_path))
    print("✅ Model loaded")

    # Connect to MongoDB
    # db = Database()
    # await db.connect()
    # print("✅ Database connected")

    # # Initialize demo inventory
    # await db.init_demo_inventory()
    # print("✅ Demo inventory initialized")

# @app.on_event("shutdown")
# async def shutdown_event():
#     """Cleanup on server shutdown"""
#     if db:
#         await db.disconnect()
#     print("👋 Server shutdown")

def parse_recipe_json(text: str) -> Dict:
    """Parse JSON output from model, handling potential formatting issues"""
    try:
        # Try direct JSON parsing
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text (in case there's extra text)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If all else fails, return error structure
        return {
            "status": "error",
            "missing_ingredients": [],
            "recipe": {
                "name": "Error",
                "cuisine": "Unknown",
                "culinary_preference": "Unknown",
                "time": "N/A",
                "main_ingredients": [],
                "steps": f"Failed to parse recipe. Raw output:\n{text}",
                "note": "Please try again"
            },
            "shopping_list": []
        }

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "PantryPilot Recipe Generator"}

@app.post("/api/generate-recipe", response_model=RecipeResponse)
async def generate_recipe(request: GenerateRecipeRequest):
    """Generate recipe based on user's natural language request and inventory"""
    try:
        # Get inventory and preferences from the request body
        inventory = [item.dict() for item in request.inventory]
        preferences = request.preferences.dict()

        if request.compare:
            # Generate with both base and fine-tuned models
            comparison = model_service.generate_comparison(
                inventory,
                preferences,
                request.user_request
            )
            base_output = comparison["base"]
            finetuned_output = comparison["finetuned"]

            # Parse JSON outputs
            base_json = parse_recipe_json(base_output)
            finetuned_json = parse_recipe_json(finetuned_output)

            return RecipeResponse(
                recipe=finetuned_json,
                base_recipe=base_json
            )
        else:
            # Generate with fine-tuned model only
            output = model_service.generate_recipe(
                inventory,
                preferences,
                request.user_request,
                use_finetuned=True
            )

            # Parse JSON output
            output_json = parse_recipe_json(output)
            return RecipeResponse(recipe=output_json)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @app.get("/api/inventory")
# async def get_inventory():
#     """Get current inventory"""
#     inventory = await db.get_inventory()
#     return {"inventory": inventory}

# @app.post("/api/inventory")
# async def add_inventory_item(item: InventoryItem):
#     """Add item to inventory"""
#     result = await db.add_inventory_item(item.dict())
#     return {"success": True, "item": result}

# @app.delete("/api/inventory/{item_name}")
# async def remove_inventory_item(item_name: str):
#     """Remove item from inventory"""
#     await db.remove_inventory_item(item_name)
#     return {"success": True, "removed": item_name}

# @app.get("/api/preferences")
# async def get_preferences():
#     """Get user preferences"""
#     prefs = await db.get_preferences()
#     return prefs

# @app.post("/api/preferences")
# async def update_preferences(preferences: UserPreferences):
#     """Update user preferences"""
#     result = await db.update_preferences(preferences.dict())
#     return {"success": True, "preferences": result}

@app.post("/api/reward")
async def submit_reward_feedback(request: RewardRequest):
    """Submit user feedback for reward model training"""
    feedback_data = {
        "user_request": request.user_request,
        "chosen_recipe": request.chosen_recipe.dict(),
        "rejected_recipe": request.rejected_recipe.dict(),
        "timestamp": datetime.now().isoformat()
    }
    feedback_file_path = Path(__file__).parent / "user_data" / "reward_model_feedback.jsonl"
    with open(feedback_file_path, "a") as f:
        f.write(json.dumps(feedback_data) + "\n")
    return {"success": True, "message": "Reward feedback submitted"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
