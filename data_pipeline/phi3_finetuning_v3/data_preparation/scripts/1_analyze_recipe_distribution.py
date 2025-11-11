#!/usr/bin/env python3
"""
Analyze Recipe1M distribution to identify gaps
Determines which categories need synthetic data generation
"""

import json
import random
from pathlib import Path
from typing import Dict, List
from collections import defaultdict, Counter
import requests
from tqdm import tqdm


class RecipeDistributionAnalyzer:
    def __init__(self, recipe_path: str, ollama_url: str = "http://localhost:11434"):
        self.recipe_path = Path(recipe_path)
        self.ollama_url = ollama_url
        self.model = "llama3.1:8b"

        # Target categories we want to track
        self.target_categories = {
            'cuisine_styles': [
                'italian', 'mexican', 'chinese', 'japanese', 'thai', 'indian',
                'mediterranean', 'french', 'korean', 'vietnamese',
                'american', 'southern', 'tex-mex', 'greek', 'middle-eastern'
            ],
            'cooking_time': [
                '<15min', '15-30min', '30-60min', '>60min'
            ],
            'difficulty': [
                'easy', 'medium', 'hard'
            ],
            'cooking_methods': [
                'grilled', 'roasted', 'baked', 'stir-fry', 'slow-cooker',
                'instant-pot', 'one-pot', 'no-cook', 'air-fryer'
            ],
            'dietary': [
                'vegan', 'vegetarian', 'pescatarian', 'omnivore',
                'gluten-free', 'dairy-free', 'nut-free', 'keto', 'paleo'
            ],
            'meal_types': [
                'breakfast', 'lunch', 'dinner', 'snack', 'dessert',
                'appetizer', 'main-course', 'side-dish'
            ]
        }

    def classify_recipe_sample(self, recipe: Dict) -> Dict:
        """Use LLM to classify a single recipe"""

        ingredient_texts = [ing['text'] for ing in recipe['ingredients'][:10]]  # First 10
        ingredients_str = ", ".join(ingredient_texts)
        title = recipe['title']

        prompt = f"""Classify this recipe into categories. Be concise and accurate.

Recipe: {title}
Ingredients: {ingredients_str}

Provide JSON with ONLY these fields (use exact values from lists):
{{
    "cuisine_style": "italian/mexican/chinese/japanese/thai/indian/mediterranean/french/korean/vietnamese/american/southern/tex-mex/greek/middle-eastern/fusion/other",
    "cooking_time": "<15min/15-30min/30-60min/>60min",
    "difficulty": "easy/medium/hard",
    "cooking_method": "grilled/roasted/baked/stir-fry/slow-cooker/instant-pot/one-pot/no-cook/air-fryer/other",
    "dietary": "vegan/vegetarian/pescatarian/omnivore",
    "meal_type": "breakfast/lunch/dinner/snack/dessert/appetizer/main-course/side-dish"
}}

Respond with ONLY valid JSON, no explanation."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "format": "json"
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')

                # Parse JSON
                classification = json.loads(response_text)
                return classification
            else:
                return None

        except Exception as e:
            print(f"Error classifying: {e}")
            return None

    def analyze_sample(self, num_samples: int = 500):
        """Analyze a sample of recipes to understand distribution"""

        print(f"📖 Loading recipes from {self.recipe_path}")
        with open(self.recipe_path, 'r') as f:
            data = json.load(f)

        train_recipes = [r for r in data if r.get('partition') == 'train']

        # Filter valid recipes
        valid_recipes = [
            r for r in train_recipes
            if len(r.get('ingredients', [])) >= 3
            and len(r.get('instructions', [])) >= 2
            and len(r.get('ingredients', [])) <= 15
        ]

        print(f"✅ Found {len(valid_recipes):,} valid recipes")
        print(f"📊 Analyzing sample of {num_samples} recipes...")

        # Sample for analysis
        sampled = random.sample(valid_recipes, min(num_samples, len(valid_recipes)))

        # Track distributions
        distributions = {
            'cuisine_style': Counter(),
            'cooking_time': Counter(),
            'difficulty': Counter(),
            'cooking_method': Counter(),
            'dietary': Counter(),
            'meal_type': Counter()
        }

        classified_samples = []

        for recipe in tqdm(sampled, desc="Classifying"):
            classification = self.classify_recipe_sample(recipe)

            if classification:
                classified_samples.append({
                    'title': recipe['title'],
                    'classification': classification
                })

                # Update distributions
                for key in distributions.keys():
                    value = classification.get(key, 'unknown')
                    distributions[key][value] += 1

        return distributions, classified_samples, len(valid_recipes)

    def identify_gaps(self, distributions: Dict, total_available: int, min_threshold: int = 50):
        """Identify categories that need synthetic data"""

        gaps = defaultdict(list)

        print("\n" + "=" * 80)
        print("�� DISTRIBUTION ANALYSIS")
        print("=" * 80)

        for category, counter in distributions.items():
            print(f"\n{category.upper()}:")
            print("-" * 60)

            total = sum(counter.values())

            # Sort by count
            for value, count in counter.most_common():
                percentage = (count / total * 100) if total > 0 else 0
                print(f"   {value:20s}: {count:4d} ({percentage:5.1f}%)")

                # Identify gaps (less than threshold)
                if count < min_threshold:
                    gaps[category].append({
                        'value': value,
                        'current_count': count,
                        'needed': min_threshold - count
                    })

        print("\n" + "=" * 80)
        print("🔍 IDENTIFIED GAPS (Need Synthetic Data)")
        print("=" * 80)

        total_synthetic_needed = 0

        for category, gap_list in gaps.items():
            if gap_list:
                print(f"\n{category.upper()}:")
                for gap in gap_list:
                    print(f"   {gap['value']:20s}: need {gap['needed']:3d} more samples (currently {gap['current_count']})")
                    total_synthetic_needed += gap['needed']

        print(f"\n📈 Total synthetic samples needed: {total_synthetic_needed}")
        print(f"📚 Total available in Recipe1M: {total_available:,}")

        return gaps

    def generate_synthesis_plan(self, gaps: Dict):
        """Generate a plan for synthetic data creation"""

        print("\n" + "=" * 80)
        print("📋 SYNTHESIS PLAN")
        print("=" * 80)

        plan = {
            'expand_existing': [],  # Augment existing recipes
            'generate_new': []      # Generate completely new recipes
        }

        # Categories that can be created by augmenting existing recipes
        augmentable = ['cooking_time', 'difficulty', 'cooking_method']

        # Categories that need new recipe generation
        need_generation = ['cuisine_style', 'meal_type']

        for category, gap_list in gaps.items():
            if category in augmentable:
                for gap in gap_list:
                    plan['expand_existing'].append({
                        'category': category,
                        'target': gap['value'],
                        'count': gap['needed'],
                        'method': 'augment'
                    })

            elif category in need_generation:
                for gap in gap_list:
                    plan['generate_new'].append({
                        'category': category,
                        'target': gap['value'],
                        'count': gap['needed'],
                        'method': 'llm_generate'
                    })

        print("\n1. AUGMENT EXISTING RECIPES:")
        print("   (Modify cooking method/time for existing recipes)")
        for item in plan['expand_existing']:
            print(f"   - {item['category']}: {item['target']} ({item['count']} samples)")

        print("\n2. GENERATE NEW RECIPES (LLM):")
        print("   (Create entirely new recipes for missing cuisines/types)")
        for item in plan['generate_new']:
            print(f"   - {item['category']}: {item['target']} ({item['count']} samples)")

        return plan


def main():
    print("🔍 Recipe Distribution Analysis")
    print("=" * 80)
    print("Goal: Identify gaps in Recipe1M dataset")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent
    recipe_path = base_dir / "data" / "recipe" / "layer1.json"

    if not recipe_path.exists():
        print(f"❌ Recipe file not found: {recipe_path}")
        return

    analyzer = RecipeDistributionAnalyzer(str(recipe_path))

    # Analyze sample
    distributions, samples, total_available = analyzer.analyze_sample(num_samples=500)

    # Identify gaps (categories with < 50 samples)
    gaps = analyzer.identify_gaps(distributions, total_available, min_threshold=50)

    # Generate synthesis plan
    plan = analyzer.generate_synthesis_plan(gaps)

    # Save results
    output_file = base_dir / "data" / "recipe" / "distribution_analysis.json"
    output_data = {
        'distributions': {k: dict(v) for k, v in distributions.items()},
        'gaps': gaps,
        'synthesis_plan': plan,
        'total_available': total_available
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Analysis saved to: {output_file}")

    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review gaps in distribution_analysis.json")
    print("2. For sparse categories, run synthetic data generation")
    print("3. For abundant categories, sample more from Recipe1M")


if __name__ == "__main__":
    main()
