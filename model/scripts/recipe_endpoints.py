from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from datetime import datetime
import os
from fastapi import FastAPI

app = FastAPI(max_request_size=100000000)

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
            "temperature": 0.7,
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
    return result

@app.post("/submit-preference")
async def submit_preference(preference: SubmitPreferenceRequest):
    data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": preference.user_id,
        "chosen_set": preference.chosen_set,
        "recipes": [recipe.model_dump() for recipe in preference.recipes]
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