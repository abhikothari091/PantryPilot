import json
import random

# --- Data Pools for Realistic Generation ---
CUISINES = ["Italian", "Mexican", "Chinese", "Indian", "Thai", "Japanese", "Mediterranean", "American"]
INGREDIENTS = ["chicken breast", "rice", "broccoli", "pasta", "tomatoes", "beef", "spinach", "paneer", "noodles", "shrimp", "garlic", "onion", "bell pepper", "mushrooms"]
ADJECTIVES = ["quick", "easy", "spicy", "healthy", "simple", "delicious", "savory"]
MEAL_TYPES = ["dinner", "lunch", "breakfast", "snack"]
COOKING_STYLES = ["Stir-fry", "Curry", "Pasta", "Tacos", "Grilled", "Salad", "Soup"]
CULINARY_PREFERENCES = ["veg", "non-veg", "vegan"]

def generate_recipe(used_ingredients):
    """Generates a single synthetic recipe."""
    cuisine = random.choice(CUISINES)
    main_ingredients = random.sample(INGREDIENTS, k=random.randint(2, 4))
    
    # Ensure generated recipe doesn't use the exact same ingredients as its pair
    while set(main_ingredients) == set(used_ingredients):
        main_ingredients = random.sample(INGREDIENTS, k=random.randint(2, 4))

    recipe_name = f"{random.choice(ADJECTIVES)} {random.choice(main_ingredients).capitalize()} {random.choice(COOKING_STYLES)}"
    
    return {
        "name": recipe_name,
        "cuisine": cuisine,
        "culinary_preference": random.choice(CULINARY_PREFERENCES),
        "time": f"{random.randint(15, 60)}m",
        "main_ingredients": main_ingredients,
        "steps": f"Step 1: Prepare the {main_ingredients[0]}. Step 2: Cook the {main_ingredients[1]}. Step 3: Combine all ingredients and cook for {random.randint(5, 15)} minutes. Step 4: Season to taste. Step 5: Serve hot.",
        "note": random.choice([None, "Can be served with a side of rice.", "Best enjoyed fresh."])
    }

def generate_synthetic_data(num_entries=50):
    """Generates a list of synthetic preference pairs."""
    synthetic_data = []
    for _ in range(num_entries):
        # 1. Generate user request
        req_ingredients = random.sample(INGREDIENTS, k=2)
        user_request = "I want a {} {} with {} and {}さんが".format(random.choice(ADJECTIVES), random.choice(MEAL_TYPES), req_ingredients[0], req_ingredients[1])

        # 2. Generate two distinct recipes
        recipe_a = generate_recipe([])
        recipe_b = generate_recipe(recipe_a["main_ingredients"])

        # 3. Randomly assign chosen and rejected
        if random.random() > 0.5:
            chosen = recipe_a
            rejected = recipe_b
        else:
            chosen = recipe_b
            rejected = recipe_a
            
        synthetic_data.append({
            "chosen_recipe": chosen,
            "rejected_recipe": rejected,
            "user_request": user_request
        })
        
    return synthetic_data

if __name__ == "__main__":
    data = generate_synthetic_data(50)
    
    # Save as a single JSON array
    with open("synthetic_reward_data.json", "w") as f:
        json.dump(data, f, indent=2)
        
    print("Successfully generated 50 synthetic reward data entries in 'synthetic_reward_data.json'")

    # Also save as JSONL for compatibility with training script
    with open("synthetic_reward_data.jsonl", "w") as f:
        for entry in data:
            f.write(json.dumps(entry) + "\n")
    
    print("Successfully generated 50 synthetic reward data entries in 'synthetic_reward_data.jsonl'")
