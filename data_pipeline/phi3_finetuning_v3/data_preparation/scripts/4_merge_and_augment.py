#!/usr/bin/env python3
"""
Merge Recipe1M + synthetic data and augment vegetarian inventories
Adds diverse meat/fish items to vegetarian samples for production-realistic training
"""

import json
import random
from pathlib import Path
from typing import Dict, List
from collections import Counter
from datetime import datetime


class DataMerger:
    def __init__(self):
        # Diverse forbidden items for inventory augmentation
        self.diverse_forbidden_items = {
            'poultry': [
                'chicken breast', 'chicken thigh', 'ground turkey',
                'turkey breast', 'duck breast', 'chicken drumsticks'
            ],
            'beef': [
                'ground beef', 'beef steak', 'sirloin steak',
                'ribeye', 'beef chuck', 'flank steak'
            ],
            'pork': [
                'bacon strips', 'pork chops', 'ham',
                'sausage', 'pepperoni', 'pork belly'
            ],
            'fish': [
                'salmon fillet', 'tuna steak', 'cod fillet',
                'tilapia', 'halibut', 'trout fillet'
            ],
            'seafood': [
                'shrimp', 'crab meat', 'lobster',
                'scallops', 'mussels', 'squid'
            ]
        }

    def load_datasets(self, base_dir: Path) -> Dict[str, List[Dict]]:
        """Load all three datasets"""

        datasets = {}

        # Recipe1M balanced samples
        recipe1m_file = base_dir / "data" / "recipe" / "balanced_samples_4334.json"
        print(f"📖 Loading Recipe1M samples: {recipe1m_file}")
        with open(recipe1m_file, 'r') as f:
            datasets['recipe1m'] = json.load(f)
        print(f"   ✅ Loaded {len(datasets['recipe1m']):,} Recipe1M samples")

        # Korean synthetic
        korean_file = base_dir / "data" / "recipe" / "synthetic_korean_286.json"
        print(f"📖 Loading Korean synthetic: {korean_file}")
        with open(korean_file, 'r') as f:
            datasets['korean'] = json.load(f)
        print(f"   ✅ Loaded {len(datasets['korean']):,} Korean synthetic samples")

        # Vietnamese synthetic
        vietnamese_file = base_dir / "data" / "recipe" / "synthetic_vietnamese_273.json"
        print(f"📖 Loading Vietnamese synthetic: {vietnamese_file}")
        with open(vietnamese_file, 'r') as f:
            datasets['vietnamese'] = json.load(f)
        print(f"   ✅ Loaded {len(datasets['vietnamese']):,} Vietnamese synthetic samples")

        return datasets

    def merge_datasets(self, datasets: Dict[str, List[Dict]]) -> List[Dict]:
        """Merge all datasets with metadata preservation"""

        print(f"\n🔄 Merging datasets...")

        merged = []

        # Add Recipe1M samples
        for recipe in datasets['recipe1m']:
            # Ensure metadata exists
            if 'metadata' not in recipe:
                recipe['metadata'] = {
                    'source': 'recipe1m',
                    'source_type': 'recipe1m_sampled'
                }
            merged.append(recipe)

        # Add Korean synthetic
        for recipe in datasets['korean']:
            # Ensure metadata exists
            if 'metadata' not in recipe:
                recipe['metadata'] = {
                    'source': 'synthetic_korean',
                    'source_type': 'llm_generated'
                }
            merged.append(recipe)

        # Add Vietnamese synthetic
        for recipe in datasets['vietnamese']:
            # Ensure metadata exists
            if 'metadata' not in recipe:
                recipe['metadata'] = {
                    'source': 'synthetic_vietnamese',
                    'source_type': 'llm_generated'
                }
            merged.append(recipe)

        print(f"   ✅ Merged {len(merged):,} total recipes")

        # Show distribution
        cuisine_counts = Counter([r['metadata'].get('cuisine', 'unknown') for r in merged])
        print(f"\n📊 Merged dataset distribution:")
        for cuisine, count in sorted(cuisine_counts.items()):
            print(f"   {cuisine:15s}: {count:4d}")

        return merged

    def augment_vegetarian_inventories(
        self,
        recipes: List[Dict],
        augmentation_ratio: float = 0.40
    ) -> List[Dict]:
        """
        Augment vegetarian samples with diverse meat/fish in inventory
        Key requirement from user: "육류 나 생선 등 을 포함시켜서 select 안하게 해야해"
        (Include various meats AND fish so model learns not to select them)
        """

        print(f"\n🥩 Augmenting vegetarian inventories...")
        print(f"   Target: {augmentation_ratio:.0%} of vegetarian samples")
        print(f"   Strategy: Add 2-3 diverse meat/fish items from different categories")

        # Identify vegetarian samples
        vegetarian_samples = [
            r for r in recipes
            if r['metadata'].get('dietary') == 'vegetarian'
        ]

        print(f"   Found {len(vegetarian_samples):,} vegetarian samples")

        # Calculate how many to augment
        num_to_augment = int(len(vegetarian_samples) * augmentation_ratio)
        samples_to_augment = random.sample(vegetarian_samples, num_to_augment)

        print(f"   Augmenting {num_to_augment:,} samples ({augmentation_ratio:.0%})")

        augmented_count = 0

        for recipe in samples_to_augment:
            # Select 2-3 diverse items from different categories
            num_items = random.choice([2, 3])

            # Randomly select categories (ensure diversity)
            categories = random.sample(list(self.diverse_forbidden_items.keys()), num_items)

            # Select one item from each category
            added_items = []
            for category in categories:
                item = random.choice(self.diverse_forbidden_items[category])
                added_items.append({
                    'text': item,
                    'category': category,
                    'forbidden': True  # Mark as forbidden (should not be selected)
                })

            # Add to recipe's ingredients (as inventory, not selected)
            if 'inventory' not in recipe:
                recipe['inventory'] = []

            # Store original ingredient count
            original_ingredient_count = len(recipe.get('ingredients', []))

            # Add forbidden items to inventory
            for item in added_items:
                recipe['inventory'].append(item)

            # Track transformation in metadata
            if 'transformations' not in recipe['metadata']:
                recipe['metadata']['transformations'] = []

            recipe['metadata']['transformations'].append({
                'type': 'inventory_augmentation',
                'timestamp': datetime.now().isoformat(),
                'added_items': [item['text'] for item in added_items],
                'categories': categories,
                'reason': 'production_realistic_diverse_meat_fish',
                'expected_behavior': 'model_should_NOT_select_these_items'
            })

            augmented_count += 1

        print(f"   ✅ Augmented {augmented_count:,} vegetarian samples")

        # Show augmentation statistics
        augmentation_stats = Counter()
        for recipe in recipes:
            if 'transformations' in recipe.get('metadata', {}):
                for transform in recipe['metadata']['transformations']:
                    if transform['type'] == 'inventory_augmentation':
                        for category in transform['categories']:
                            augmentation_stats[category] += 1

        print(f"\n📊 Augmentation statistics:")
        for category, count in sorted(augmentation_stats.items()):
            print(f"   {category:10s}: {count:4d} samples")

        return recipes

    def create_inventory_from_ingredients(self, recipes: List[Dict]) -> List[Dict]:
        """
        Create inventory field from ingredients if not exists
        This prepares recipes for the next phase (LLM generation)
        """

        print(f"\n📦 Creating inventory fields...")

        for recipe in recipes:
            if 'inventory' not in recipe:
                # Copy ingredients to inventory
                recipe['inventory'] = []
                for ing in recipe.get('ingredients', []):
                    recipe['inventory'].append({
                        'text': ing.get('text', ''),
                        'forbidden': False  # Original ingredients are not forbidden
                    })

        print(f"   ✅ Created inventory for {len(recipes):,} recipes")

        return recipes

    def validate_augmentation(self, recipes: List[Dict]):
        """Validate that augmentation was successful"""

        print(f"\n✅ Validating augmentation...")

        total_vegetarian = 0
        augmented_vegetarian = 0
        total_forbidden_items = 0

        for recipe in recipes:
            if recipe['metadata'].get('dietary') == 'vegetarian':
                total_vegetarian += 1

                # Check if augmented
                if 'transformations' in recipe['metadata']:
                    for transform in recipe['metadata']['transformations']:
                        if transform['type'] == 'inventory_augmentation':
                            augmented_vegetarian += 1
                            total_forbidden_items += len(transform['added_items'])
                            break

        augmentation_percentage = (augmented_vegetarian / total_vegetarian * 100) if total_vegetarian > 0 else 0
        avg_forbidden_per_sample = (total_forbidden_items / augmented_vegetarian) if augmented_vegetarian > 0 else 0

        print(f"   Total vegetarian samples: {total_vegetarian:,}")
        print(f"   Augmented samples: {augmented_vegetarian:,} ({augmentation_percentage:.1f}%)")
        print(f"   Total forbidden items added: {total_forbidden_items:,}")
        print(f"   Avg forbidden items per augmented sample: {avg_forbidden_per_sample:.1f}")

        # Show example
        for recipe in recipes:
            if 'transformations' in recipe.get('metadata', {}):
                for transform in recipe['metadata']['transformations']:
                    if transform['type'] == 'inventory_augmentation':
                        print(f"\n🔍 Example augmented recipe:")
                        print(f"   Title: {recipe.get('title', 'N/A')}")
                        print(f"   Cuisine: {recipe['metadata'].get('cuisine', 'N/A')}")
                        print(f"   Dietary: {recipe['metadata'].get('dietary', 'N/A')}")
                        print(f"   Added forbidden items: {', '.join(transform['added_items'])}")
                        break
                break


def main():
    print("🔄 Dataset Merger and Augmentation")
    print("=" * 80)
    print("Goal: Merge Recipe1M + synthetic data + augment vegetarian inventories")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent

    # Initialize merger
    merger = DataMerger()

    # Load datasets
    datasets = merger.load_datasets(base_dir)

    # Merge
    merged_recipes = merger.merge_datasets(datasets)

    # Create inventory fields
    merged_recipes = merger.create_inventory_from_ingredients(merged_recipes)

    # Augment vegetarian inventories with diverse meat/fish
    augmented_recipes = merger.augment_vegetarian_inventories(
        merged_recipes,
        augmentation_ratio=0.40  # 40% of vegetarian samples
    )

    # Validate
    merger.validate_augmentation(augmented_recipes)

    # Save merged and augmented dataset
    output_file = base_dir / "data" / "recipe" / f"merged_augmented_{len(augmented_recipes)}.json"

    with open(output_file, 'w') as f:
        json.dump(augmented_recipes, f, indent=2)

    print(f"\n💾 Saved {len(augmented_recipes):,} recipes to: {output_file}")

    # Summary
    print("\n" + "=" * 80)
    print("✅ Merge and Augmentation Complete!")
    print("=" * 80)
    print(f"\nDataset composition:")
    print(f"   Recipe1M samples: {len(datasets['recipe1m']):,}")
    print(f"   Korean synthetic: {len(datasets['korean']):,}")
    print(f"   Vietnamese synthetic: {len(datasets['vietnamese']):,}")
    print(f"   Total: {len(augmented_recipes):,}")

    dietary_counts = Counter([r['metadata'].get('dietary', 'unknown') for r in augmented_recipes])
    print(f"\nDietary distribution:")
    for dietary, count in sorted(dietary_counts.items()):
        print(f"   {dietary:15s}: {count:4d}")

    print(f"\nNext step: Generate enriched training data with LLM (~4-5 hours)")


if __name__ == "__main__":
    random.seed(42)  # Reproducibility
    main()
