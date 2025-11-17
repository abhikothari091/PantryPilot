"""
Validate training samples for dietary constraint violations
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


class DietaryValidator:
    def __init__(self):
        # Dietary restriction rules
        self.meat_keywords = ['chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb', 'bacon',
                              'sausage', 'ham', 'steak', 'meat', 'salmon', 'tuna', 'shrimp',
                              'chorizo', 'crawfish', 'crab']

        self.dairy_keywords = ['milk', 'cheese', 'butter', 'cream', 'yogurt', 'cheddar',
                               'mozzarella', 'parmesan', 'cottage cheese', 'whey', 'casein']

        self.egg_keywords = ['egg', 'eggs']

        self.gluten_keywords = ['flour', 'bread', 'pasta', 'wheat', 'barley', 'rye',
                                'noodle', 'cake', 'cookie', 'cracker']

    def extract_selected_ingredients(self, training_text: str) -> List[str]:
        """Extract selected ingredients from assistant response"""
        # Find the assistant response section
        if '<|assistant|>' not in training_text:
            return []

        assistant_section = training_text.split('<|assistant|>')[1]
        if '<|end|>' in assistant_section:
            assistant_section = assistant_section.split('<|end|>')[0]

        # Extract "Selected ingredients from your pantry:" section
        if 'Selected ingredients from your pantry:' not in assistant_section:
            return []

        selected_section = assistant_section.split('Selected ingredients from your pantry:')[1]

        # Stop at "Suggested additions" or "Instructions"
        if 'Suggested additions' in selected_section:
            selected_section = selected_section.split('Suggested additions')[0]
        elif 'Instructions:' in selected_section:
            selected_section = selected_section.split('Instructions:')[0]

        # Extract ingredient lines (start with -)
        ingredients = []
        for line in selected_section.strip().split('\n'):
            line = line.strip()
            if line.startswith('-'):
                ingredient = line[1:].strip()
                if ingredient:
                    ingredients.append(ingredient.lower())

        return ingredients

    def check_vegetarian_violation(self, dietary_tags: List[str], ingredients: List[str]) -> Tuple[bool, List[str]]:
        """Check if vegetarian restriction is violated"""
        if 'vegetarian' not in dietary_tags and 'vegan' not in dietary_tags:
            return False, []

        violations = []
        for ing in ingredients:
            for meat in self.meat_keywords:
                if meat in ing:
                    violations.append(f"{ing} (contains: {meat})")
                    break

        return len(violations) > 0, violations

    def check_dairy_free_violation(self, dietary_tags: List[str], ingredients: List[str]) -> Tuple[bool, List[str]]:
        """Check if dairy-free restriction is violated"""
        if 'dairy-free' not in dietary_tags:
            return False, []

        violations = []
        for ing in ingredients:
            for dairy in self.dairy_keywords:
                if dairy in ing:
                    violations.append(f"{ing} (contains: {dairy})")
                    break

        return len(violations) > 0, violations

    def check_vegan_violation(self, dietary_tags: List[str], ingredients: List[str]) -> Tuple[bool, List[str]]:
        """Check if vegan restriction is violated"""
        if 'vegan' not in dietary_tags:
            return False, []

        violations = []

        # Check for meat
        for ing in ingredients:
            for meat in self.meat_keywords:
                if meat in ing:
                    violations.append(f"{ing} (meat: {meat})")
                    break

        # Check for dairy
        for ing in ingredients:
            for dairy in self.dairy_keywords:
                if dairy in ing:
                    violations.append(f"{ing} (dairy: {dairy})")
                    break

        # Check for eggs
        for ing in ingredients:
            for egg in self.egg_keywords:
                if egg in ing:
                    violations.append(f"{ing} (egg)")
                    break

        return len(violations) > 0, violations

    def validate_sample(self, sample: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single sample

        Returns:
            (is_valid, violation_messages)
        """
        dietary_tags = sample['metadata'].get('dietary_tags', [])
        training_text = sample['text']

        # Extract selected ingredients
        ingredients = self.extract_selected_ingredients(training_text)

        if not ingredients:
            return True, []  # Skip if can't extract ingredients

        all_violations = []

        # Check vegetarian
        has_violation, violations = self.check_vegetarian_violation(dietary_tags, ingredients)
        if has_violation:
            all_violations.extend([f"VEGETARIAN: {v}" for v in violations])

        # Check dairy-free
        has_violation, violations = self.check_dairy_free_violation(dietary_tags, ingredients)
        if has_violation:
            all_violations.extend([f"DAIRY-FREE: {v}" for v in violations])

        # Check vegan
        has_violation, violations = self.check_vegan_violation(dietary_tags, ingredients)
        if has_violation:
            all_violations.extend([f"VEGAN: {v}" for v in violations])

        is_valid = len(all_violations) == 0
        return is_valid, all_violations


def main():
    input_file = Path(__file__).parent.parent / "data" / "finetune" / "inventory_aware_v2_5000.jsonl"
    output_file = Path(__file__).parent.parent / "data" / "finetune" / "inventory_aware_v2_5000_filtered.jsonl"

    print(f"📂 Reading: {input_file}")

    # Load samples
    samples = []
    with open(input_file, 'r') as f:
        for line in f:
            samples.append(json.loads(line))

    print(f"✅ Loaded {len(samples)} samples\n")

    # Validate
    validator = DietaryValidator()
    valid_samples = []
    invalid_samples = []

    print("🔍 Validating dietary constraints...\n")

    for i, sample in enumerate(samples, 1):
        is_valid, violations = validator.validate_sample(sample)

        if is_valid:
            valid_samples.append(sample)
        else:
            invalid_samples.append((sample, violations))
            print(f"❌ Sample {i}: {sample['metadata']['recipe_title']}")
            print(f"   Dietary tags: {sample['metadata']['dietary_tags']}")
            for violation in violations:
                print(f"   - {violation}")
            print()

    # Summary
    print("="*80)
    print(f"📊 VALIDATION SUMMARY")
    print("="*80)
    print(f"Total samples: {len(samples)}")
    print(f"✅ Valid samples: {len(valid_samples)} ({len(valid_samples)/len(samples)*100:.1f}%)")
    print(f"❌ Invalid samples: {len(invalid_samples)} ({len(invalid_samples)/len(samples)*100:.1f}%)")
    print()

    # Save valid samples
    with open(output_file, 'w') as f:
        for sample in valid_samples:
            f.write(json.dumps(sample) + '\n')

    print(f"💾 Saved {len(valid_samples)} valid samples to:")
    print(f"   {output_file}")
    print()

    # Show invalid sample details
    if invalid_samples:
        print(f"⚠️  Removed {len(invalid_samples)} samples with violations")


if __name__ == "__main__":
    main()
