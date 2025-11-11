#!/usr/bin/env python3
"""
Sample balanced recipes from Recipe1M
Creates uniform distribution across cuisines and dietary constraints
"""

import json
import random
from pathlib import Path
from typing import Dict, List
from collections import defaultdict, Counter
from datetime import datetime


class BalancedRecipeSampler:
    def __init__(self, recipe_path: str):
        self.recipe_path = Path(recipe_path)

        # Cuisine keywords (from analysis)
        self.cuisine_keywords = {
            'italian': ['pasta', 'pizza', 'risotto', 'italian', 'parmesan', 'parmigiano', 'lasagna', 'spaghetti', 'ravioli', 'gnocchi'],
            'mediterranean': ['mediterranean', 'greek', 'feta', 'hummus', 'tzatziki', 'gyro', 'olive oil'],
            'chinese': ['stir fry', 'chinese', 'wok', 'soy sauce', 'fried rice', 'chow mein', 'szechuan'],
            'mexican': ['taco', 'burrito', 'salsa', 'mexican', 'enchilada', 'quesadilla', 'guacamole', 'tortilla'],
            'thai': ['thai', 'pad thai', 'curry', 'coconut milk', 'lemongrass', 'fish sauce'],
            'american': ['american', 'burger', 'bbq', 'grilled cheese', 'mac and cheese'],
            'indian': ['curry', 'indian', 'tandoori', 'masala', 'tikka', 'naan', 'biryani'],
            'japanese': ['japanese', 'sushi', 'teriyaki', 'miso', 'ramen', 'tempura', 'udon'],
            'korean': ['korean', 'kimchi', 'bibimbap', 'gochujang', 'bulgogi'],
            'vietnamese': ['vietnamese', 'pho', 'banh', 'nuoc mam'],
        }

        # Comprehensive meat keywords
        self.meat_keywords = [
            'chicken', 'beef', 'pork', 'lamb', 'turkey', 'duck',
            'bacon', 'ham', 'sausage', 'pepperoni', 'prosciutto',
            'fish', 'salmon', 'tuna', 'cod', 'tilapia',
            'shrimp', 'crab', 'lobster', 'seafood',
            'chicken stock', 'beef stock', 'beef broth', 'chicken broth',
        ]

    def load_and_classify_recipes(self) -> Dict[str, List[Dict]]:
        """Load Recipe1M and classify into bins"""

        print(f"📖 Loading recipes from {self.recipe_path}...")
        with open(self.recipe_path, 'r') as f:
            data = json.load(f)

        # Filter valid recipes
        valid_recipes = [
            r for r in data
            if r.get('partition') == 'train'
            and len(r.get('ingredients', [])) >= 3
            and len(r.get('instructions', [])) >= 2
            and len(r.get('ingredients', [])) <= 15
        ]

        print(f"✅ Found {len(valid_recipes):,} valid recipes")
        print(f"\n🏃 Classifying into bins...")

        # Create bins
        bins = {}
        for cuisine in self.cuisine_keywords.keys():
            bins[cuisine] = {
                'vegetarian': [],
                'omnivore': []
            }
        bins['unmatched'] = {'vegetarian': [], 'omnivore': []}

        # Classify each recipe
        for recipe in valid_recipes:
            title = recipe.get('title', '').lower()
            ingredients_text = ' '.join([ing.get('text', '').lower() for ing in recipe.get('ingredients', [])])
            text = title + ' ' + ingredients_text

            # Classify cuisine
            cuisine_match = None
            for cuisine, keywords in self.cuisine_keywords.items():
                if any(kw in text for kw in keywords):
                    cuisine_match = cuisine
                    break

            if not cuisine_match:
                cuisine_match = 'unmatched'

            # Classify dietary (check for meat)
            has_meat = any(kw in text for kw in self.meat_keywords)
            dietary = 'omnivore' if has_meat else 'vegetarian'

            # Add to bin
            bins[cuisine_match][dietary].append(recipe)

        # Print distribution
        print(f"\n📊 Recipe distribution by cuisine and dietary:")
        for cuisine in sorted(bins.keys()):
            if cuisine == 'unmatched':
                continue
            veg_count = len(bins[cuisine]['vegetarian'])
            omni_count = len(bins[cuisine]['omnivore'])
            total = veg_count + omni_count
            print(f"   {cuisine:15s}: {total:6,} total ({veg_count:6,} veg, {omni_count:6,} omni)")

        return bins

    def sample_balanced(
        self,
        bins: Dict[str, List[Dict]],
        target_per_cuisine: int = 500,
        dietary_ratio: Dict[str, float] = None
    ) -> List[Dict]:
        """Sample balanced recipes from bins"""

        if dietary_ratio is None:
            dietary_ratio = {
                'vegetarian': 0.30,
                'omnivore': 0.70  # Includes pescatarian later
            }

        print(f"\n🎯 Sampling {target_per_cuisine} recipes per cuisine...")
        print(f"   Dietary ratio: vegetarian={dietary_ratio['vegetarian']:.0%}, omnivore={dietary_ratio['omnivore']:.0%}")

        sampled_recipes = []
        sampling_summary = {}

        for cuisine in self.cuisine_keywords.keys():
            if cuisine not in bins:
                continue

            # Calculate targets
            target_veg = int(target_per_cuisine * dietary_ratio['vegetarian'])
            target_omni = target_per_cuisine - target_veg

            # Sample vegetarian
            available_veg = len(bins[cuisine]['vegetarian'])
            sampled_veg = min(target_veg, available_veg)
            veg_samples = random.sample(bins[cuisine]['vegetarian'], sampled_veg) if available_veg > 0 else []

            # Sample omnivore
            available_omni = len(bins[cuisine]['omnivore'])
            sampled_omni = min(target_omni, available_omni)
            omni_samples = random.sample(bins[cuisine]['omnivore'], sampled_omni) if available_omni > 0 else []

            # Add metadata
            for recipe in veg_samples:
                recipe['metadata'] = {
                    'source': 'recipe1m',
                    'source_type': 'recipe1m_sampled',
                    'source_partition': 'train',
                    'original_index': data.index(recipe) if 'data' in locals() else -1,
                    'sampling_timestamp': datetime.now().isoformat(),
                    'cuisine': cuisine,
                    'dietary': 'vegetarian',
                    'distribution': {
                        'cuisine_bin': cuisine,
                        'dietary_bin': 'vegetarian',
                        'target_count': target_veg,
                        'bin_index': len(sampled_recipes)
                    }
                }
                sampled_recipes.append(recipe)

            for recipe in omni_samples:
                recipe['metadata'] = {
                    'source': 'recipe1m',
                    'source_type': 'recipe1m_sampled',
                    'source_partition': 'train',
                    'original_index': -1,
                    'sampling_timestamp': datetime.now().isoformat(),
                    'cuisine': cuisine,
                    'dietary': 'omnivore',
                    'distribution': {
                        'cuisine_bin': cuisine,
                        'dietary_bin': 'omnivore',
                        'target_count': target_omni,
                        'bin_index': len(sampled_recipes)
                    }
                }
                sampled_recipes.append(recipe)

            sampling_summary[cuisine] = {
                'target_veg': target_veg,
                'sampled_veg': sampled_veg,
                'target_omni': target_omni,
                'sampled_omni': sampled_omni,
                'total': sampled_veg + sampled_omni
            }

            print(f"   {cuisine:15s}: {sampled_veg+sampled_omni:3d}/{target_per_cuisine} ({sampled_veg} veg, {sampled_omni} omni)")

        return sampled_recipes, sampling_summary


def main():
    print("🎯 Balanced Recipe Sampling from Recipe1M")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent
    recipe_path = base_dir / "data" / "recipe" / "layer1.json"

    # Initialize sampler
    sampler = BalancedRecipeSampler(str(recipe_path))

    # Load and classify
    bins = sampler.load_and_classify_recipes()

    # Sample balanced
    # Target: 500 per cuisine × 10 cuisines = 5000
    # But Korean (214) and Vietnamese (227) are short, so adjust
    target_distribution = {
        'italian': 500,
        'mediterranean': 500,
        'chinese': 500,
        'mexican': 500,
        'thai': 500,
        'american': 500,
        'indian': 500,
        'japanese': 500,
        'korean': 214,      # All available
        'vietnamese': 227,  # All available
    }

    # Sample each cuisine
    all_samples = []
    for cuisine, target in target_distribution.items():
        if cuisine not in bins:
            continue

        target_veg = int(target * 0.30)
        target_omni = target - target_veg

        # Sample
        veg_available = len(bins[cuisine]['vegetarian'])
        omni_available = len(bins[cuisine]['omnivore'])

        veg_samples = random.sample(bins[cuisine]['vegetarian'], min(target_veg, veg_available)) if veg_available > 0 else []
        omni_samples = random.sample(bins[cuisine]['omnivore'], min(target_omni, omni_available)) if omni_available > 0 else []

        # Add metadata
        for recipe in veg_samples + omni_samples:
            recipe['metadata'] = {
                'source': 'recipe1m',
                'cuisine': cuisine,
                'dietary': 'vegetarian' if recipe in veg_samples else 'omnivore',
            }

        all_samples.extend(veg_samples + omni_samples)

    # Save
    output_file = base_dir / "data" / "recipe" / f"balanced_samples_{len(all_samples)}.json"
    with open(output_file, 'w') as f:
        json.dump(all_samples, f, indent=2)

    print(f"\n💾 Saved {len(all_samples)} balanced recipes to: {output_file}")

    # Summary
    print(f"\n📊 Final distribution:")
    cuisine_counts = Counter([s['metadata']['cuisine'] for s in all_samples])
    for cuisine, count in sorted(cuisine_counts.items()):
        print(f"   {cuisine:15s}: {count:4d}")

    print("\n" + "=" * 80)
    print("✅ Balanced Sampling Complete!")
    print("=" * 80)
    print(f"\nTotal sampled: {len(all_samples)}")
    print(f"Missing for 5000: Korean ({500-214}), Vietnamese ({500-227})")
    print(f"Next: Generate {500-214+500-227} synthetic recipes")


if __name__ == "__main__":
    random.seed(42)  # Reproducibility
    main()
