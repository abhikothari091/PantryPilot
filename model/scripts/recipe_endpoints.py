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
    priority_threshold: int = 7
    num_recipes: int = 3

class RecipeResponse(BaseModel):
    name: str
    time: int
    main_ingredients: List[str]
    quick_steps: str
    cuisine: str

class SubmitPreferenceRequest(BaseModel):
    user_id: str
    chosen_set: str
    recipes: List[RecipeResponse]

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b-instruct-q4_K_M"

def calculate_priority_items(inventory: List[InventoryItem], threshold: int = 7) -> List[str]:
    priority = []
    for item in inventory:
        if item.days_in >= threshold:
            priority.append(f"{item.item} ({item.days_in} days)")
    return sorted(priority, key=lambda x: int(x.split('(')[1].split()[0]), reverse=True)

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
    priority_items = calculate_priority_items(request.inventory, request.priority_threshold)
    meal_type = determine_meal_type(request.time)
    all_items = [item.item for item in request.inventory]

    prompt = f"""
    Generate exactly 2 sets of {meal_type} recipes using the ingredients below.

    Priority ingredients (use these first - they're older):
    {', '.join(priority_items[:6])}

    All available ingredients:
    {', '.join(all_items)}

    Each set should have exactly {request.num_recipes} recipes.

    Return only valid JSON like this:
    {{
        "Set A": [
            {{"name": "Recipe 1", "cuisine": "Cuisine", "time": 25, "main_ingredients": ["ingredient1", "ingredient2"], "quick_steps": "Quick steps..."}},
            {{"name": "Recipe 2", "cuisine": "Cuisine", "time": 30, "main_ingredients": ["ingredient3", "ingredient4"], "quick_steps": "Quick steps..."}}
        ],
        "Set B": [
            {{"name": "Recipe 1", "cuisine": "Cuisine", "time": 20, "main_ingredients": ["ingredient1", "ingredient2"], "quick_steps": "Quick steps..."}},
            {{"name": "Recipe 2", "cuisine": "Cuisine", "time": 35, "main_ingredients": ["ingredient3", "ingredient4"], "quick_steps": "Quick steps..."}}
        ]
    }}
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
            "max_tokens": 1000
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        response_text = result.get("response", "[]")

        if isinstance(response_text, str):
            response_text = response_text.strip()

            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]

            try:
                recipes_json = json.loads(response_text)
            except json.JSONDecodeError:
                print(f"Failed to parse: {response_text}")
                raise HTTPException(status_code=500, detail=f"Failed to parse model response.")
        else:
            recipes_json = response_text

        if isinstance(recipes_json, dict):
            set_a = recipes_json.get("Set A", [])
            set_b = recipes_json.get("Set B", [])
        else:
            set_a, set_b = [], []

        return {"Set A": set_a, "Set B": set_b}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse: {response_text}")
        raise HTTPException(status_code=500, detail="Failed to parse model response.")

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
