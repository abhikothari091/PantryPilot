#!/usr/bin/env python3
"""
Split training data into train/valid and clean violations
Removes samples where forbidden items were incorrectly selected
"""

import json
import random
from pathlib import Path
from typing import Dict, List
from collections import Counter


class TrainingDataCleaner:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)

    def load_data(self) -> List[Dict]:
        """Load enriched training data"""
        print(f"\n📖 Loading training data from: {self.data_path}")

        with open(self.data_path, 'r') as f:
            data = json.load(f)

        print(f"   ✅ Loaded {len(data):,} samples")
        return data

    def analyze_violations(self, data: List[Dict]) -> Dict:
        """Analyze validation results"""

        print(f"\n🔍 Analyzing validation results...")

        total = len(data)
        augmented = sum(1 for s in data if s['metadata'].get('augmented', False))

        violations = []
        correctly_avoided = []

        for sample in data:
            metadata = sample['metadata']
            validation = metadata.get('validation', {})

            if validation.get('has_forbidden_items', False):
                if validation.get('selected_forbidden', False):
                    violations.append(sample)
                else:
                    correctly_avoided.append(sample)

        print(f"\n📊 Validation Analysis:")
        print(f"   Total samples: {total:,}")
        print(f"   Augmented (with forbidden items): {augmented:,} ({augmented/total*100:.1f}%)")
        print(f"   Correctly avoided forbidden: {len(correctly_avoided):,}")
        print(f"   ❌ VIOLATIONS (selected forbidden): {len(violations):,}")

        if violations:
            print(f"\n⚠️  Found {len(violations)} violation samples that need to be removed!")

            # Show violation examples
            for i, violation in enumerate(violations[:3]):
                print(f"\n   Violation {i+1}:")
                print(f"      Recipe: {violation['metadata']['recipe_title']}")
                print(f"      Dietary: {violation['metadata']['dietary']}")
                print(f"      Forbidden items: {violation['metadata']['forbidden_items_in_inventory'][:3]}")

        return {
            'total': total,
            'augmented': augmented,
            'violations': violations,
            'correctly_avoided': correctly_avoided,
            'clean_samples': [s for s in data if s not in violations]
        }

    def split_train_valid(
        self,
        clean_data: List[Dict],
        train_ratio: float = 0.9
    ) -> tuple:
        """Split data into train and validation sets"""

        print(f"\n✂️  Splitting into train/valid...")
        print(f"   Ratio: {train_ratio:.0%} train, {1-train_ratio:.0%} valid")

        # Shuffle
        random.shuffle(clean_data)

        # Split
        split_idx = int(len(clean_data) * train_ratio)
        train_data = clean_data[:split_idx]
        valid_data = clean_data[split_idx:]

        print(f"   Train: {len(train_data):,} samples")
        print(f"   Valid: {len(valid_data):,} samples")

        # Analyze split distribution
        train_dietary = Counter([s['metadata']['dietary'] for s in train_data])
        valid_dietary = Counter([s['metadata']['dietary'] for s in valid_data])

        print(f"\n📊 Train dietary distribution:")
        for dietary, count in sorted(train_dietary.items()):
            print(f"      {dietary:15s}: {count:4d} ({count/len(train_data)*100:.1f}%)")

        print(f"\n📊 Valid dietary distribution:")
        for dietary, count in sorted(valid_dietary.items()):
            print(f"      {dietary:15s}: {count:4d} ({count/len(valid_data)*100:.1f}%)")

        return train_data, valid_data

    def save_datasets(
        self,
        train_data: List[Dict],
        valid_data: List[Dict],
        output_dir: Path
    ):
        """Save train and valid datasets"""

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        train_file = output_dir / "train.json"
        valid_file = output_dir / "valid.json"

        with open(train_file, 'w') as f:
            json.dump(train_data, f, indent=2)

        with open(valid_file, 'w') as f:
            json.dump(valid_data, f, indent=2)

        print(f"\n💾 Saved datasets:")
        print(f"   Train: {train_file} ({len(train_data):,} samples)")
        print(f"   Valid: {valid_file} ({len(valid_data):,} samples)")

        # Also save as JSONL for MLX
        train_jsonl = output_dir / "train.jsonl"
        valid_jsonl = output_dir / "valid.jsonl"

        with open(train_jsonl, 'w') as f:
            for sample in train_data:
                f.write(json.dumps(sample) + '\n')

        with open(valid_jsonl, 'w') as f:
            for sample in valid_data:
                f.write(json.dumps(sample) + '\n')

        print(f"\n💾 Saved JSONL datasets:")
        print(f"   Train: {train_jsonl}")
        print(f"   Valid: {valid_jsonl}")


def main():
    print("✂️  Training Data Split and Clean")
    print("=" * 80)
    print("Goal: Split into train/valid and remove violation samples")
    print("=" * 80)

    base_dir = Path(__file__).parent.parent

    # Input file
    data_file = base_dir / "data" / "finetune" / "enriched_training_data_5000.json"

    if not data_file.exists():
        print(f"❌ Data file not found: {data_file}")
        return

    # Initialize cleaner
    cleaner = TrainingDataCleaner(str(data_file))

    # Load data
    data = cleaner.load_data()

    # Analyze violations
    analysis = cleaner.analyze_violations(data)

    # Get clean data
    clean_data = analysis['clean_samples']

    if len(analysis['violations']) > 0:
        print(f"\n⚠️  Removed {len(analysis['violations'])} violation samples")
        print(f"   Clean samples remaining: {len(clean_data):,}")
    else:
        print(f"\n✅ No violations found! All {len(clean_data):,} samples are clean")

    # Split into train/valid
    train_data, valid_data = cleaner.split_train_valid(clean_data, train_ratio=0.9)

    # Save datasets
    output_dir = base_dir / "data" / "finetune"
    cleaner.save_datasets(train_data, valid_data, output_dir)

    print("\n" + "=" * 80)
    print("✅ Split and Clean Complete!")
    print("=" * 80)
    print(f"\nFinal dataset:")
    print(f"   Train: {len(train_data):,} samples")
    print(f"   Valid: {len(valid_data):,} samples")
    print(f"   Removed: {len(analysis['violations'])} violation samples")

    print(f"\nNext step: Fine-tune with MLX")
    print(f"   mlx_lm.lora --model microsoft/Phi-3-mini-4k-instruct \\")
    print(f"               --train --data data/finetune \\")
    print(f"               --iters 1000 --learning-rate 5e-5")


if __name__ == "__main__":
    random.seed(42)  # Reproducibility
    main()
