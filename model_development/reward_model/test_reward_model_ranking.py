import requests
import json
import torch
import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Assuming this script is run from the project root directory
from model.scripts.reward_model import RewardModel, RecipeEmbedder, PreferenceDataset

# --- Configuration ---
API_URL = "http://localhost:8000/generate-recipe-sets"
REWARD_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'reward_model.pth')

# --- 1. Define Requests ---
# Shared inventory that can support both cuisines
shared_inventory = [
    {"item": "chicken breast", "qty": "500g", "days_in": 2},
    {"item": "onion", "qty": "1 large", "days_in": 5},
    {"item": "garlic", "qty": "3 cloves", "days_in": 7},
    {"item": "tomatoes", "qty": "400g", "days_in": 4},
    {"item": "rice", "qty": "1kg", "days_in": 10},
    {"item": "olive oil", "qty": "100ml", "days_in": 30},
    {"item": "ginger", "qty": "1 inch", "days_in": 7},
    {"item": "yogurt", "qty": "200g", "days_in": 3},
    {"item": "garam masala", "qty": "50g", "days_in": 365}
]

# Request for an Indian recipe
indian_request = {
  "inventory": shared_inventory,
  "time": "19:00",
  "dietary_preference": "non-veg",
  "user_request": "I want an Indian dinner with chicken",
  "num_recipes": 1
}

# Request for an Italian recipe
italian_request = {
  "inventory": shared_inventory,
  "time": "19:00",
  "dietary_preference": "non-veg",
  "user_request": "I want an Italian dinner with chicken",
  "num_recipes": 1
}

# --- 2. Generate Recipes ---
def generate_recipe(request_payload):
    """Calls the API to generate a single recipe."""
    try:
        response = requests.post(API_URL, json=request_payload, timeout=60)
        response.raise_for_status()
        recipes = response.json().get("recipes", [])
        if recipes:
            # The response now includes scores, so we extract the recipe part
            return recipes[0].get("recipe") if "recipe" in recipes[0] else recipes[0]
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error generating recipe: {e}")
        return None

print("--- Generating Recipes ---")
print("1. Requesting an Indian recipe...")
indian_recipe = generate_recipe(indian_request)

print("2. Requesting an Italian recipe...")
italian_recipe = generate_recipe(italian_request)

if not (indian_recipe and italian_recipe):
    print("\nCould not generate one or both recipes. Aborting test.")
else:
    print("\n--- Generated Recipes ---")
    print(f"Indian Recipe: {indian_recipe.get('name')}")
    print(f"Italian Recipe: {italian_recipe.get('name')}")

    # --- 3. Score Recipes with Reward Model ---
    print("\n--- Scoring Recipes against INDIAN request ---")
    
    # Load the trained reward model
    embedder = RecipeEmbedder()
    embedding_dim = embedder.model.get_sentence_embedding_dimension()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reward_model = RewardModel(input_dim=embedding_dim * 2)
    
    if os.path.exists(REWARD_MODEL_PATH):
        reward_model.load_state_dict(torch.load(REWARD_MODEL_PATH, map_location=device))
        reward_model.to(device)
        reward_model.eval()
        print("RewardModel loaded successfully.")

        # Use a dummy dataset to access the text formatter
        dummy_dataset = PreferenceDataset([])
        
        recipes_to_score = [indian_recipe, italian_recipe]
        scored_recipes = []

        with torch.no_grad():
            for recipe in recipes_to_score:
                # We score both recipes against the INDIAN request
                request_text = dummy_dataset._format_recipe_as_text(recipe={}, request=indian_request)
                recipe_text = dummy_dataset._format_recipe_as_text(recipe=recipe, request=indian_request)
                
                request_embedding = embedder.embed([request_text]).to(device)
                recipe_embedding = embedder.embed([recipe_text]).to(device)
                
                combined_embedding = torch.cat((request_embedding, recipe_embedding), dim=1)
                score = reward_model(combined_embedding).item()
                scored_recipes.append({"score": score, "recipe": recipe})

        # Sort by score to see the ranking
        scored_recipes.sort(key=lambda x: x["score"], reverse=True)

        print("\n--- Scoring Results ---")
        for item in scored_recipes:
            print(f"Score: {item['score']:.4f}, Recipe: {item['recipe']['name']} ({item['recipe']['cuisine']})")

    else:
        print(f"WARNING: Reward model not found at {REWARD_MODEL_PATH}. Cannot score recipes.")
