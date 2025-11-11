#!/usr/bin/env python3
"""
Generate synthetic recipes for underrepresented cuisines
Uses LLM to create realistic recipes with balanced dietary distribution
"""

import json
import random
import argparse
from pathlib import Path
from typing import Dict, List
import requests
from tqdm import tqdm
from datetime import datetime


class SyntheticCuisineGenerator:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"

        # Cuisine-specific characteristics
        self.cuisine_profiles = {
            'korean': {
                'common_ingredients': [
                    'gochujang', 'soy sauce', 'sesame oil', 'garlic', 'ginger',
                    'green onion', 'kimchi', 'rice', 'nori', 'tofu',
                    'mushrooms', 'gochugaru', 'mirin', 'rice vinegar'
                ],
                'meat_items': [
                    'beef', 'pork belly', 'chicken', 'seafood'
                ],
                'cooking_methods': [
                    'stir-fry', 'grilled', 'steamed', 'braised', 'fermented'
                ],
                'example_dishes': [
                    'Bibimbap', 'Kimchi Stew', 'Japchae', 'Bulgogi',
                    'Korean Fried Tofu', 'Vegetable Kimbap'
                ]
            },
            'vietnamese': {
                'common_ingredients': [
                    'rice noodles', 'fish sauce', 'lime', 'cilantro', 'mint',
                    'basil', 'bean sprouts', 'lemongrass', 'chili', 'garlic',
                    'tofu', 'rice paper', 'peanuts', 'coconut milk'
                ],
                'meat_items': [
                    'pork', 'chicken', 'beef', 'shrimp', 'fish'
                ],
                'cooking_methods': [
                    'steamed', 'grilled', 'stir-fry', 'fresh/no-cook', 'simmered'
                ],
                'example_dishes': [
                    'Pho', 'Banh Mi', 'Spring Rolls', 'Bun Cha',
                    'Vegetarian Pho', 'Tofu Banh Mi'
                ]
            }
        }

    def generate_recipe(
        self,
        cuisine: str,
        dietary: str,
        meal_type: str = 'dinner'
    ) -> Dict:
        """Generate a single recipe with specific characteristics"""

        profile = self.cuisine_profiles[cuisine]

        # Build prompt
        dietary_constraints = {
            'vegetarian': 'NO meat or fish. Can use dairy and eggs. Focus on vegetables, tofu, legumes.',
            'vegan': 'NO animal products at all. No meat, fish, dairy, eggs, or honey. Use plant-based ingredients only.',
            'omnivore': 'Can include meat, poultry, or seafood.',
            'pescatarian': 'NO meat or poultry. Can include fish and seafood. Can use dairy and eggs.'
        }

        constraint = dietary_constraints[dietary]

        prompt = f"""Create a realistic {cuisine} {dietary} {meal_type} recipe.

Cuisine: {cuisine.title()}
Dietary: {dietary.title()}
Meal type: {meal_type}

Dietary constraints: {constraint}

Common {cuisine} ingredients: {', '.join(profile['common_ingredients'][:10])}
Typical cooking methods: {', '.join(profile['cooking_methods'])}
Example dishes for inspiration: {', '.join(profile['example_dishes'][:3])}

Provide a complete recipe in JSON format:
{{
    "title": "specific {cuisine} dish name",
    "ingredients": [
        {{"text": "ingredient with quantity (e.g., 2 cups rice)"}},
        {{"text": "ingredient with quantity"}}
    ],
    "instructions": [
        {{"text": "detailed step 1"}},
        {{"text": "detailed step 2"}}
    ]
}}

Requirements:
- 6-12 ingredients (authentic {cuisine} ingredients)
- 4-8 instruction steps (authentic {cuisine} cooking techniques)
- MUST respect dietary constraints: {constraint}
- Realistic quantities and measurements
- Title should be specific (e.g., "Korean Spicy Tofu Stew" not just "Tofu Stew")

Respond with ONLY valid JSON, no explanation."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.8,  # Creative
                    "format": "json"
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')

                # Parse JSON
                recipe = json.loads(response_text)

                # Validate
                if not recipe.get('title') or not recipe.get('ingredients') or not recipe.get('instructions'):
                    return None

                # Add metadata
                recipe['partition'] = 'synthetic'

                return recipe
            else:
                return None

        except Exception as e:
            print(f"Error generating recipe: {e}")
            return None

    def generate_batch(
        self,
        cuisine: str,
        dietary_distribution: Dict[str, int]
    ) -> List[Dict]:
        """Generate batch of recipes with dietary distribution"""

        recipes = []
        total = sum(dietary_distribution.values())

        print(f"\n🔨 Generating {total} {cuisine} recipes...")
        print(f"   Distribution: {dietary_distribution}")

        # Generate for each dietary type
        for dietary, count in dietary_distribution.items():
            print(f"\n   Generating {count} {dietary} recipes...")

            for i in tqdm(range(count), desc=f"  {dietary}"):
                # Vary meal types
                meal_type = random.choice(['dinner', 'lunch', 'dinner', 'lunch', 'appetizer'])

                recipe = self.generate_recipe(cuisine, dietary, meal_type)

                if recipe:
                    # Add comprehensive metadata
                    recipe['metadata'] = {
                        'source': f'synthetic_{cuisine}',
                        'source_type': 'llm_generated',
                        'generation_timestamp': datetime.now().isoformat(),
                        'generation_model': self.model,
                        'dietary': dietary,
                        'cuisine': cuisine,
                        'meal_type': meal_type,
                        'target_distribution': {
                            'cuisine_bin': cuisine,
                            'dietary_bin': dietary,
                            'target_count': dietary_distribution[dietary],
                            'bin_index': i
                        }
                    }

                    recipes.append(recipe)
                else:
                    print(f"    ⚠️  Failed to generate recipe {i+1}/{count}")

        print(f"\n   ✅ Generated {len(recipes)}/{total} recipes")

        return recipes


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic cuisine recipes')
    parser.add_argument('--cuisine', required=True, choices=['korean', 'vietnamese'],
                      help='Cuisine to generate')
    parser.add_argument('--count', type=int, required=True,
                      help='Total number of recipes to generate')
    parser.add_argument('--vegetarian', type=int, help='Number of vegetarian recipes')
    parser.add_argument('--omnivore', type=int, help='Number of omnivore recipes')
    parser.add_argument('--vegan', type=int, help='Number of vegan recipes')
    parser.add_argument('--pescatarian', type=int, help='Number of pescatarian recipes')

    args = parser.parse_args()

    print("🤖 Synthetic Cuisine Recipe Generator")
    print("=" * 80)
    print(f"Cuisine: {args.cuisine.title()}")
    print(f"Target count: {args.count}")
    print("=" * 80)

    # Calculate dietary distribution
    if args.vegetarian:
        dietary_distribution = {
            'vegetarian': args.vegetarian,
            'omnivore': args.omnivore,
            'vegan': args.vegan,
            'pescatarian': args.pescatarian
        }
    else:
        # Default distribution (30% veg, 50% omni, 10% vegan, 10% pesc)
        dietary_distribution = {
            'vegetarian': int(args.count * 0.30),
            'omnivore': int(args.count * 0.50),
            'vegan': int(args.count * 0.10),
            'pescatarian': int(args.count * 0.10)
        }

        # Adjust for rounding
        total = sum(dietary_distribution.values())
        if total != args.count:
            dietary_distribution['omnivore'] += (args.count - total)

    # Generate
    generator = SyntheticCuisineGenerator()
    recipes = generator.generate_batch(args.cuisine, dietary_distribution)

    # Save
    base_dir = Path(__file__).parent.parent
    output_file = base_dir / "data" / "recipe" / f"synthetic_{args.cuisine}_{len(recipes)}.json"

    with open(output_file, 'w') as f:
        json.dump(recipes, f, indent=2)

    print(f"\n💾 Saved {len(recipes)} recipes to: {output_file}")

    # Show examples
    print("\n🔍 Sample recipes:")
    for i, recipe in enumerate(recipes[:3]):
        print(f"\n{i+1}. {recipe['title']}")
        print(f"   Dietary: {recipe['metadata']['dietary']}")
        print(f"   Ingredients: {len(recipe['ingredients'])}")
        print(f"   Instructions: {len(recipe['instructions'])}")

    print("\n" + "=" * 80)
    print("✅ Generation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
