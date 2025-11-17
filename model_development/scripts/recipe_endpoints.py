from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from datetime import datetime
import os
from fastapi import FastAPI

import torch
from model.scripts.reward_model import RewardModel, RecipeEmbedder, PreferenceDataset, predict_best_recipe

app = FastAPI(max_request_size=100000000)

# Global variables for reward model
REWARD_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), # This script's directory
    '..', 'backend', 'reward_model.pth' 
)
reward_model_global = None
embedder_global = None
dummy_dataset_global = None # For accessing formatter

def load_reward_model_globals():
    global reward_model_global, embedder_global, dummy_dataset_global
    if reward_model_global is None:
        print("Loading SentenceTransformer and RewardModel globally...")
        embedder_global = RecipeEmbedder()
        embedding_dim = embedder_global.model.get_sentence_embedding_dimension()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        reward_model_global = RewardModel(input_dim=embedding_dim * 2)
        
        if os.path.exists(REWARD_MODEL_PATH):
            reward_model_global.load_state_dict(torch.load(REWARD_MODEL_PATH, map_location=device))
            reward_model_global.to(device)
            reward_model_global.eval()
            print("RewardModel loaded successfully.")
        else:
            print(f"WARNING: Reward model not found at {REWARD_MODEL_PATH}. Re-ranking will not be performed.")
            reward_model_global = None # Ensure it's None if not found
        
        dummy_dataset_global = PreferenceDataset([]) # For accessing formatter
    return reward_model_global, embedder_global, dummy_dataset_global

# Call this function when the app starts
load_reward_model_globals()

class InventoryItem(BaseModel):
    item: str
    qty: str
    days_in: int

class RecipeRequest(BaseModel):
    inventory: List[InventoryItem]
    time: str = "18:00"
    dietary_preference: str = "non-veg"  # "vegan", "veg", or "nonveg"
    num_recipes: int = 3

class RecipeResponse(BaseModel):
    name: str
    tag: str
    cuisine: str
    time: str
    servings: str 
    ingredients: List[str]
    steps: str

class SubmitPreferenceRequest(BaseModel):
    user_id: str
    chosen_set: str
    recipes: List[RecipeResponse]
    request: RecipeRequest

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M"

def determine_meal_type(time_str: str) -> str:
    try:
        hour = int(time_str.split(':')[0])
        if 5 <= hour < 11:
            return "breakfast"
        elif 11 <= hour < 15:
            return "lunch"
        elif 15 <= hour < 17:
            return "snack"
        elif 17 <= hour < 22:
            return "dinner"
        else:
            return "late night snack"
    except:
        return "meal"

def format_dual_prompt(request: RecipeRequest) -> str:
    meal_type = determine_meal_type(request.time)
    
    # Create quantity-aware ingredient list
    ingredients_with_qty = [
        f"{item.item}: {item.qty}" for item in request.inventory
    ]
    
    dietary_instructions = {
        "vegan": "plant-only ingredients (no meat, dairy, eggs, or animal products)",
        "veg": "vegetarian ingredients (no meat/seafood, but dairy/eggs allowed)",
        "non-veg": "any ingredients including meat, seafood, and poultry"
    }
    
    diet_constraint = dietary_instructions.get(request.dietary_preference, dietary_instructions["non-veg"])

    prompt = f"""
    Generate exactly {request.num_recipes} recipes using the ingredients below. You MUST ONLY output valid JSON. No commentary. No markdown. No text outside JSON.

    Available ingredients with quantities:
    {chr(10).join(ingredients_with_qty)}

    CRITICAL CONSTRAINTS:
    - Use ONLY ingredients from the list above. Do NOT assume availability of any other ingredients.
    - Recipes must respect available quantities (if inventory has 500g chicken, don't require 1kg).
    - If common cooking basics (salt, pepper) are not in the list, you MAY assume small amounts are available.
    - Scale recipes to fit available quantities OR choose different recipes.
    - DO NOT generate recipes requiring more than available quantities.

    Dietary preference: {request.dietary_preference}
    Use ONLY {diet_constraint}.

    Requirements for each recipe:
    - Include a "tag" field: use "{request.dietary_preference}" for all recipes. 
    - Include "generated_at" with the current date and time.
    - Include a "servings" field: specify how many people this recipe serves (e.g., "2 people", "4 people").
    - Include a "cuisine" field: specify the COOKING STYLE/ORIGIN, not the ingredient type.
    Valid examples: "Italian", "Mexican", "Thai", "Indian", "Japanese", "Mediterranean", "American", "Chinese"
    INVALID examples: "Poultry", "Seafood", "Vegetarian", "Meat" - these are NOT cuisines
    - "time" must include units ("10m", "45s", "1h", etc.)
    - "ingredients" must list ALL ingredients used in the recipe with measurements.
    - Every ingredient mentioned in steps MUST appear in the ingredients array.
    - Include cooking oils, seasonings, garnishes, and everything else in the ingredients list.
    - "steps" must contain at least 5 steps, detailed but concise.
    
    CRITICAL: The dietary restriction applies to:
    - All ingredients listed
    - All cooking ingredients (oils, sauces, broths)
    - All serving suggestions (bread, rice, sides)
    - All garnishes and toppings
    - Everything mentioned in the recipe steps

    Do NOT suggest serving with items that violate the dietary preference.

    Return ONLY valid JSON array in this exact format:
    [
        {{
            "name": "Recipe 1",
            "tag": "{request.dietary_preference}",
            "cuisine": "Cuisine",
            "time": "25m",
            "servings": "2 people",
            "ingredients": ["ingredient1 (1 cup)", "ingredient2 (2 tbsp)"],
            "steps": "Step 1. Step 2. Step 3. Step 4. Step 5."
        }}
    ]
    """

    return prompt


def call_ollama(prompt: str) -> dict:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.9,
            "top_p": 0.9,
            "max_tokens": 2000,
            "format": "json"
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()

        if "response" not in result:
            raise HTTPException(status_code=500, detail="Ollama response missing 'response'.")

        try:
            recipes_json = json.loads(result["response"])
        except json.JSONDecodeError:
            print("FAILED INPUT:", result["response"])
            raise HTTPException(status_code=500, detail=f"Failed to decode JSON from model.")

        # Expect array of recipes
        if isinstance(recipes_json, list):
            return {"recipes": recipes_json}
        else:
            return {"recipes": []}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")


@app.post("/generate-recipe-sets")
async def generate_recipe_sets(request: RecipeRequest):
    prompt = format_dual_prompt(request)
    result = call_ollama(prompt)
    
    generated_recipes = result.get("recipes", [])

    if reward_model_global and generated_recipes:
        print("Re-ranking recipes using reward model...")
        
        scored_recipes = []
        with torch.no_grad():
            for recipe in generated_recipes:
                request_text = dummy_dataset_global.formatter(recipe={}, request=request.model_dump())
                recipe_text = dummy_dataset_global.formatter(recipe=recipe, request=request.model_dump())
                
                request_embedding = embedder_global.embed([request_text]).to(embedder_global.device)
                recipe_embedding = embedder_global.embed([recipe_text]).to(embedder_global.device)
                
                combined_embedding = torch.cat((request_embedding, recipe_embedding), dim=1)
                score = reward_model_global(combined_embedding).item()
                scored_recipes.append((score, recipe))
        
        # Sort by score in descending order
        scored_recipes.sort(key=lambda x: x[0], reverse=True)
        
        # Create a new list with score and recipe
        scored_and_ranked_recipes = [{"score": score, "recipe": recipe} for score, recipe in scored_recipes]
        
        result["recipes"] = scored_and_ranked_recipes
        print("Recipes re-ranked with scores.")

    return result

@app.post("/submit-preference")
async def submit_preference(preference: SubmitPreferenceRequest):
    data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": preference.user_id,
        "chosen_set": preference.chosen_set,
        "recipes": [recipe.model_dump() for recipe in preference.recipes],
        "request": preference.request.model_dump()
    }

    user_data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_data")
    os.makedirs(user_data_path, exist_ok=True)

    with open(f"{user_data_path}/{preference.user_id}_preferences.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")

    return {"status": "saved"}

@app.get("/health")
async def health_check():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return {"status": "healthy", "ollama": "connected"}
    except:
        return {"status": "degraded", "ollama": "disconnected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)