import torch
import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from model.scripts.reward_model import RewardModel, RecipeEmbedder, PreferenceDataset

# --- Configuration ---
REWARD_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'reward_model.pth')

# --- 1. Define Hardcoded, Distinct Recipes and Request ---
print("--- Defining Test Data ---")

# A simple, generic request
test_request = {
    "user_query": "I want a healthy dinner.",
    "inventory": [{"item": "chicken", "qty": "500g"}, {"item": "lettuce", "qty": "1 head"}],
    "dietary_preference": "non-veg"
}

# Recipe 1: A simple salad
recipe_1 = {
    "name": "Simple Chicken Salad",
    "cuisine": "American",
    "ingredients": ["chicken", "lettuce", "olive oil", "lemon juice"],
    "steps": "1. Grill chicken. 2. Chop lettuce. 3. Mix all ingredients."
}
print("Recipe 1: Simple Chicken Salad")

# Recipe 2: A completely different curry
recipe_2 = {
    "name": "Spicy Chicken Curry",
    "cuisine": "Indian",
    "ingredients": ["chicken", "onion", "garlic", "garam masala", "coconut milk"],
    "steps": "1. Sauté onion and garlic. 2. Add chicken and spices. 3. Simmer with coconut milk."
}
print("Recipe 2: Spicy Chicken Curry")

# --- 2. Load Model and Embedder ---
print("\n--- Loading Models ---")
if not os.path.exists(REWARD_MODEL_PATH):
    print(f"ERROR: Reward model not found at {REWARD_MODEL_PATH}. Aborting.")
    sys.exit(1)

embedder = RecipeEmbedder()
embedding_dim = embedder.model.get_sentence_embedding_dimension()
device = "cuda" if torch.cuda.is_available() else "cpu"
reward_model = RewardModel(input_dim=embedding_dim * 2)
reward_model.load_state_dict(torch.load(REWARD_MODEL_PATH, map_location=device))
reward_model.to(device)
reward_model.eval()
print("RewardModel and Embedder loaded successfully.")

# --- 3. Manually Process and Score Each Recipe ---
print("\n--- Processing and Scoring ---")

# Use a dummy dataset to access the text formatter
dummy_dataset = PreferenceDataset([])

def score_recipe(recipe, request):
    """Manually performs all steps to score a single recipe."""
    print(f"\nScoring Recipe: '{recipe['name']}'")
    
    # Step A: Format text
    request_text = dummy_dataset._format_recipe_as_text(recipe={}, request=request)
    recipe_text = dummy_dataset._format_recipe_as_text(recipe=recipe, request=request)
    print(f"  Formatted Text (first 80 chars): {recipe_text[:80]}...")
    
    # Step B: Generate embeddings
    with torch.no_grad():
        request_embedding = embedder.embed([request_text]).to(device)
        recipe_embedding = embedder.embed([recipe_text]).to(device)
        
        # Print a slice of the embedding to see if they are different
        print(f"  Recipe Embedding (first 5 values): {recipe_embedding[0, :5].tolist()}")
        
        # Step C: Combine embeddings
        combined_embedding = torch.cat((request_embedding, recipe_embedding), dim=1)
        
        # Step D: Get score from reward model
        score = reward_model(combined_embedding).item()
        print(f"  => FINAL SCORE: {score}")
        return score

# Score both recipes
score_1 = score_recipe(recipe_1, test_request)
score_2 = score_recipe(recipe_2, test_request)

print("\n--- Final Comparison ---")
print(f"Score for '{recipe_1['name']}': {score_1}")
print(f"Score for '{recipe_2['name']}': {score_2}")

if score_1 == score_2:
    print("\nConclusion: The scores are identical. The reward model has likely collapsed and is not differentiating between inputs.")
else:
    print("\nConclusion: The scores are different. The reward model is producing varied outputs.")
