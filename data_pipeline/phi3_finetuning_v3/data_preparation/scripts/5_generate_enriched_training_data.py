#!/usr/bin/env python3
"""
Generate enriched training data from merged and augmented recipes
Uses Llama 3.1 8B via Ollama to create production-realistic training samples
"""

import json
import random
from pathlib import Path
from typing import Dict, List
import requests
from tqdm import tqdm
from datetime import datetime


class EnrichedTrainingDataGenerator:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"

        # Common pantry items to add to inventory
        self.common_pantry = [
            "salt", "black pepper", "olive oil", "vegetable oil", "butter",
            "sugar", "flour", "eggs", "milk", "garlic", "onion",
            "soy sauce", "vinegar", "rice", "pasta", "bread",
            "tomato paste", "oregano", "basil", "thyme", "paprika",
            "cumin", "chili powder", "ginger", "lemon juice", "honey"
        ]

        # Common ingredients by category for adding variety
        self.common_ingredients = {
            'vegetables': [
                'bell pepper', 'carrot', 'celery', 'broccoli', 'cauliflower',
                'spinach', 'kale', 'lettuce', 'cucumber', 'zucchini'
            ],
            'proteins': [
                'tofu', 'chickpeas', 'black beans', 'lentils', 'quinoa'
            ],
            'grains': [
                'white rice', 'brown rice', 'couscous', 'bulgur', 'oats'
            ],
            'dairy': [
                'cheese', 'yogurt', 'cream', 'parmesan', 'mozzarella'
            ]
        }

    def create_production_inventory(self, recipe: Dict) -> List[Dict]:
        """
        Create production-realistic inventory
        - Uses augmented inventory if available (includes forbidden items)
        - Adds common pantry items
        - Adds random ingredients for variety
        """

        inventory = []

        # Use existing inventory if available (from augmentation)
        if 'inventory' in recipe:
            inventory = recipe['inventory'].copy()
        else:
            # Create from ingredients
            for ing in recipe.get('ingredients', []):
                inventory.append({
                    'text': ing.get('text', ''),
                    'forbidden': False
                })

        # Add 8-12 common pantry items
        num_pantry = random.randint(8, 12)
        for item in random.sample(self.common_pantry, num_pantry):
            inventory.append({
                'text': item,
                'forbidden': False
            })

        # Add 3-5 random ingredients from different categories
        num_random = random.randint(3, 5)
        random_items = []
        for category in random.sample(list(self.common_ingredients.keys()), min(3, len(self.common_ingredients))):
            random_items.extend(random.sample(self.common_ingredients[category], 1))

        for item in random_items[:num_random]:
            inventory.append({
                'text': item,
                'forbidden': False
            })

        # Shuffle to make it realistic
        random.shuffle(inventory)

        return inventory

    def generate_user_request(self, recipe: Dict) -> str:
        """
        Generate natural user request using LLM
        Uses metadata (cuisine, dietary) to create contextual request
        """

        metadata = recipe.get('metadata', {})
        cuisine = metadata.get('cuisine', 'general')
        dietary = metadata.get('dietary', 'omnivore')
        title = recipe.get('title', '')

        # Get first few ingredients for context
        ingredients_preview = []
        for ing in recipe.get('ingredients', [])[:5]:
            ingredients_preview.append(ing.get('text', ''))

        prompt = f"""Generate a natural, conversational user request for a recipe with these characteristics:

Cuisine: {cuisine}
Dietary preference: {dietary}
Recipe type: {title}
Key ingredients: {', '.join(ingredients_preview[:3])}

Create a realistic user request that someone might naturally say. Examples:
- "I want something healthy for dinner tonight"
- "Can you suggest a quick vegetarian lunch?"
- "I'm craving spicy Asian food"
- "What can I make for breakfast with eggs?"
- "Need a comfort food recipe for tonight"

Requirements:
- Be conversational and natural
- Don't just list ingredients or say the recipe name
- Incorporate the dietary preference naturally if vegetarian/vegan
- Mention cuisine style or cooking preference

Respond with ONLY the user request text, no explanation."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.8,  # Creative
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                user_request = result.get('response', '').strip()

                # Remove quotes if LLM added them
                user_request = user_request.strip('"\'')

                return user_request if user_request else f"I'd like to make a {dietary} {cuisine} dish"
            else:
                return f"I'd like to make a {dietary} {cuisine} dish"

        except Exception as e:
            print(f"  ⚠️  LLM request generation failed: {e}")
            return f"I'd like to make a {dietary} {cuisine} dish"

    def format_phi3_training_sample(
        self,
        recipe: Dict,
        inventory: List[Dict],
        user_request: str
    ) -> Dict:
        """
        Format as Phi-3 instruction training sample
        Critical: Model must NOT select forbidden items
        """

        metadata = recipe.get('metadata', {})
        dietary = metadata.get('dietary', 'omnivore')

        # Format inventory for display
        inventory_lines = []
        forbidden_items = []
        for item in inventory:
            inventory_lines.append(f"- {item['text']}")
            if item.get('forbidden', False):
                forbidden_items.append(item['text'])

        inventory_str = "\n".join(inventory_lines)

        # Build dietary constraint description
        dietary_constraints = {
            'vegetarian': 'vegetarian (no meat or fish)',
            'vegan': 'vegan (no animal products)',
            'omnivore': 'no specific dietary restrictions',
            'pescatarian': 'pescatarian (no meat, fish is ok)'
        }
        dietary_desc = dietary_constraints.get(dietary, dietary)

        # System instruction
        system_instruction = f"""You are a creative recipe generator with access to the user's pantry inventory.

Available ingredients in pantry:
{inventory_str}

User dietary preference: {dietary_desc}

Instructions:
1. Based on the user's request, select appropriate ingredients from the available inventory
2. IMPORTANT: Respect dietary restrictions - do NOT select meat/fish for vegetarian/vegan recipes
3. Generate a complete, practical recipe with clear steps
4. You may suggest 1-2 common pantry items if absolutely needed

Output format:
Recipe: [Recipe Name]

Selected ingredients from your pantry:
- [ingredient 1]
- [ingredient 2]
...

Instructions:
1. [Step 1]
2. [Step 2]
..."""

        # Build expected output (from recipe)
        # Select only non-forbidden ingredients that are in inventory
        inventory_texts = [item['text'] for item in inventory]
        recipe_ingredient_texts = [ing.get('text', '') for ing in recipe.get('ingredients', [])]

        selected_ingredients = []
        for ing_text in recipe_ingredient_texts:
            # Find if this ingredient is in inventory
            matching_inv = [item for item in inventory if item['text'] == ing_text]
            if matching_inv:
                # Check if forbidden
                if not matching_inv[0].get('forbidden', False):
                    selected_ingredients.append(ing_text)

        output_parts = [f"Recipe: {recipe.get('title', 'Untitled Recipe')}\n"]

        output_parts.append("Selected ingredients from your pantry:")
        for ing in selected_ingredients:
            output_parts.append(f"- {ing}")
        output_parts.append("")

        output_parts.append("Instructions:")
        instruction_texts = [inst.get('text', '') for inst in recipe.get('instructions', [])]
        for i, step in enumerate(instruction_texts, 1):
            output_parts.append(f"{i}. {step}")

        expected_output = "\n".join(output_parts)

        # Phi-3 format
        phi3_prompt = f"""<|system|>
{system_instruction}<|end|>
<|user|>
{user_request}<|end|>
<|assistant|>
{expected_output}<|end|>"""

        # Validate: ensure no forbidden items were selected
        validation = {
            'has_forbidden_items': len(forbidden_items) > 0,
            'forbidden_items': forbidden_items,
            'selected_forbidden': any(f in expected_output for f in forbidden_items),
            'correctly_avoided': len(forbidden_items) > 0 and not any(f in expected_output for f in forbidden_items)
        }

        return {
            "text": phi3_prompt,
            "metadata": {
                "recipe_title": recipe.get('title', ''),
                "cuisine": metadata.get('cuisine', 'unknown'),
                "dietary": dietary,
                "source": metadata.get('source', 'unknown'),
                "source_type": metadata.get('source_type', 'unknown'),
                "augmented": len(forbidden_items) > 0,
                "forbidden_items_in_inventory": forbidden_items,
                "inventory_size": len(inventory),
                "selected_ingredients_count": len(selected_ingredients),
                "validation": validation,
                "user_request": user_request,
                "generation_timestamp": datetime.now().isoformat()
            }
        }

    def generate_training_data(
        self,
        recipes: List[Dict],
        target_count: int = 5000
    ) -> List[Dict]:
        """
        Generate enriched training data from recipes
        """

        print(f"\n🔨 Generating {target_count} enriched training samples...")
        print(f"   Source recipes: {len(recipes)}")

        # Sample recipes (with replacement if needed)
        if len(recipes) < target_count:
            print(f"   Note: Sampling with replacement ({target_count} > {len(recipes)})")
            sampled_recipes = random.choices(recipes, k=target_count)
        else:
            sampled_recipes = random.sample(recipes, target_count)

        training_samples = []
        failed_count = 0

        # Progress tracking file
        progress_file = Path(__file__).parent.parent / "data" / "finetune" / "generation_progress.txt"
        progress_file.parent.mkdir(parents=True, exist_ok=True)

        for idx, recipe in enumerate(tqdm(sampled_recipes, desc="Generating samples")):
            try:
                # Create production inventory
                inventory = self.create_production_inventory(recipe)

                # Generate user request with LLM
                user_request = self.generate_user_request(recipe)

                # Format as Phi-3 training sample
                sample = self.format_phi3_training_sample(recipe, inventory, user_request)

                training_samples.append(sample)

                # Save progress every 100 samples
                if (idx + 1) % 100 == 0:
                    with open(progress_file, 'w') as f:
                        f.write(f"Progress: {idx + 1}/{target_count} ({(idx+1)/target_count*100:.1f}%)\n")
                        f.write(f"Failed: {failed_count}\n")
                        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    print(f"\n   📊 Progress: {idx+1}/{target_count} ({(idx+1)/target_count*100:.1f}%)")

            except Exception as e:
                print(f"\n  ⚠️  Failed to generate sample: {e}")
                failed_count += 1

        print(f"\n   ✅ Generated {len(training_samples)} samples")
        if failed_count > 0:
            print(f"   ⚠️  Failed: {failed_count} samples")

        return training_samples

    def validate_training_data(self, samples: List[Dict]):
        """Validate generated training data"""

        print(f"\n✅ Validating training data...")

        total = len(samples)
        augmented_count = sum(1 for s in samples if s['metadata'].get('augmented', False))
        correctly_avoided = sum(
            1 for s in samples
            if s['metadata'].get('validation', {}).get('correctly_avoided', False)
        )

        dietary_dist = {}
        for s in samples:
            dietary = s['metadata'].get('dietary', 'unknown')
            dietary_dist[dietary] = dietary_dist.get(dietary, 0) + 1

        print(f"   Total samples: {total:,}")
        print(f"   Augmented samples (with forbidden items): {augmented_count:,} ({augmented_count/total*100:.1f}%)")
        print(f"   Correctly avoided forbidden items: {correctly_avoided:,}")

        print(f"\n   Dietary distribution:")
        for dietary, count in sorted(dietary_dist.items()):
            print(f"      {dietary:15s}: {count:4d} ({count/total*100:.1f}%)")

        # Show example
        augmented_samples = [s for s in samples if s['metadata'].get('augmented', False)]
        if augmented_samples:
            example = augmented_samples[0]
            print(f"\n   🔍 Example augmented sample:")
            print(f"      Recipe: {example['metadata']['recipe_title']}")
            print(f"      Dietary: {example['metadata']['dietary']}")
            print(f"      Forbidden items in inventory: {', '.join(example['metadata']['forbidden_items_in_inventory'][:3])}")
            print(f"      Correctly avoided: {example['metadata']['validation']['correctly_avoided']}")


def main():
    print("🚀 Enriched Training Data Generation")
    print("=" * 80)
    print("Goal: Generate 5,000 production-realistic training samples")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent

    # Load merged and augmented recipes
    recipe_file = base_dir / "data" / "recipe" / "merged_augmented_4893.json"

    if not recipe_file.exists():
        print(f"❌ Recipe file not found: {recipe_file}")
        return

    print(f"\n📖 Loading recipes from: {recipe_file}")
    with open(recipe_file, 'r') as f:
        recipes = json.load(f)

    print(f"   ✅ Loaded {len(recipes):,} recipes")

    # Initialize generator
    generator = EnrichedTrainingDataGenerator()

    # Generate training data
    training_samples = generator.generate_training_data(
        recipes,
        target_count=5000
    )

    # Validate
    generator.validate_training_data(training_samples)

    # Save
    output_file = base_dir / "data" / "finetune" / f"enriched_training_data_{len(training_samples)}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(training_samples, f, indent=2)

    print(f"\n💾 Saved {len(training_samples):,} training samples to:")
    print(f"   {output_file}")

    print("\n" + "=" * 80)
    print("✅ Training Data Generation Complete!")
    print("=" * 80)
    print(f"\nNext step: Split into train/valid and clean violations")


if __name__ == "__main__":
    random.seed(42)  # Reproducibility
    main()
