from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from datetime import datetime

app = FastAPI()

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

def format_prompt(request: RecipeRequest) -> str:
    priority_items = calculate_priority_items(request.inventory, request.priority_threshold)
    meal_type = determine_meal_type(request.time)
    
    all_items = [item.item for item in request.inventory]
    
    prompt = f"""Generate exactly {request.num_recipes} {meal_type} recipes for {request.time}.
    
    Priority ingredients (use these first - they're older):
    {', '.join(priority_items[:6])}

    All available ingredients:
    {', '.join(all_items)}

    IMPORTANT: Return ONLY a valid JSON array with exactly {request.num_recipes} recipes. No other text before or after the JSON.

    [
    {{"name": "Recipe 1 Name", "time": 30, "main_ingredients": ["ingredient1", "ingredient2", "ingredient3"], "quick_steps": "Step by step cooking instructions in one line"}},
    {{"name": "Recipe 2 Name", "time": 25, "main_ingredients": ["ingredient1", "ingredient2"], "quick_steps": "Step by step cooking instructions in one line"}},
    {{"name": "Recipe 3 Name", "time": 35, "main_ingredients": ["ingredient1", "ingredient2", "ingredient3"], "quick_steps": "Step by step cooking instructions in one line"}}
    ]"""
    
    return prompt

def call_ollama(prompt: str) -> list:
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
            
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            try:
                recipes_json = json.loads(response_text)
            except json.JSONDecodeError:
                if not response_text.startswith('['):
                    response_text = f"[{response_text}]"
                recipes_json = json.loads(response_text)
        else:
            recipes_json = response_text
            
        if isinstance(recipes_json, dict):
            recipes_json = [recipes_json]
        elif not isinstance(recipes_json, list):
            recipes_json = []
            
        return recipes_json
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse: {result.get('response', 'No response')}")
        raise HTTPException(status_code=500, detail=f"Failed to parse model response: {str(e)}")

@app.post("/generate-recipes", response_model=List[RecipeResponse])
async def generate_recipes(request: RecipeRequest):
    prompt = format_prompt(request)
    
    try:
        recipes = call_ollama(prompt)
        
        validated_recipes = []
        for recipe in recipes:
            if isinstance(recipe, dict):
                validated_recipes.append(RecipeResponse(
                    name=recipe.get("name", "Unknown Recipe"),
                    time=recipe.get("time", 30),
                    main_ingredients=recipe.get("main_ingredients", []),
                    quick_steps=recipe.get("quick_steps", "")
                ))
        
        if not validated_recipes:
            validated_recipes = [RecipeResponse(
                name="Recipe Generation Failed",
                time=30,
                main_ingredients=["Please try again"],
                quick_steps="The model didn't return valid recipes"
            )]
        
        return validated_recipes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return {"status": "healthy", "ollama": "connected"}
    except:
        return {"status": "degraded", "ollama": "disconnected"}

@app.post("/generate-recipes-custom")
async def generate_recipes_custom(
    inventory: List[InventoryItem],
    time: str = "18:00", 
    priority_items: Optional[List[str]] = None,
    num_recipes: int = 3
):
    meal_type = determine_meal_type(time)
    
    if priority_items:
        priority_text = ', '.join(priority_items)
    else:
        priority_items = calculate_priority_items(inventory)
        priority_text = ', '.join(priority_items[:6])
    
    all_items = [item.item for item in inventory]
    
    prompt = f"""Generate {num_recipes} {meal_type} recipes.
    Priority items to use: {priority_text}
    Available: {', '.join(all_items)}

    Return JSON array:
    [{{"name": "", "time": 0, "main_ingredients": [], "quick_steps": ""}}]"""
    
    recipes = call_ollama(prompt)
    return recipes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)