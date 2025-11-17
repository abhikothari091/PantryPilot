"""
Convert cleaned recipe dataset to ChatML format with natural language.
Generates conversational prompts for each scenario.
"""

import json
import random
from pathlib import Path
from typing import Dict, Optional


# Set random seed for reproducibility
random.seed(42)


# Natural language templates for each scenario
SCENARIO_1_REQUESTS = [
    "What can I cook for dinner?",
    "Suggest me a recipe.",
    "I'm hungry, make something.",
    "What should I make with these ingredients?",
    "Give me a recipe idea.",
    "Help me cook something.",
    "I want to make dinner.",
    "What can I prepare?",
    "Recommend a dish.",
    "Create a recipe for me."
]

PREFERENCE_REQUESTS = {
    "vegan": [
        "I want a vegan recipe.",
        "Make me something vegan.",
        "I'm vegan, what can I cook?",
        "Vegan recipe please.",
        "I need a plant-based dish.",
    ],
    "vegetarian": [
        "I want a vegetarian recipe.",
        "I'm vegetarian, what can I make?",
        "Vegetarian dish please.",
        "Make me something vegetarian.",
        "I don't eat meat.",
    ],
    "non-dairy": [
        "I can't have dairy, what can I make?",
        "Dairy-free recipe please.",
        "I'm lactose intolerant.",
        "No dairy products.",
        "Give me a non-dairy recipe.",
    ],
    "non_dairy": [  # Handle underscore variant
        "I can't have dairy, what can I make?",
        "Dairy-free recipe please.",
        "I'm lactose intolerant.",
        "No dairy products.",
        "Give me a non-dairy recipe.",
    ],
    "pescatarian": [
        "I'm pescatarian, what can I cook?",
        "Pescatarian recipe please.",
        "I eat fish but no meat.",
        "Seafood or vegetarian dish.",
        "Make me a pescatarian meal.",
    ],
    "gluten-free": [
        "I'm gluten-free, what can I make?",
        "Gluten-free recipe please.",
        "I can't have gluten.",
        "No wheat or gluten.",
        "Give me a gluten-free dish.",
    ],
    "gluten_free": [  # Handle underscore variant
        "I'm gluten-free, what can I make?",
        "Gluten-free recipe please.",
        "I can't have gluten.",
        "No wheat or gluten.",
        "Give me a gluten-free dish.",
    ],
    "keto": [
        "I'm on keto, what can I cook?",
        "Keto recipe please.",
        "Low-carb dish.",
        "Make me a keto meal.",
        "I need a ketogenic recipe.",
    ],
    "paleo": [
        "I'm doing paleo, what can I make?",
        "Paleo recipe please.",
        "I follow paleo diet.",
        "Make me a paleo dish.",
        "Give me a paleo-friendly meal.",
    ],
}

CUISINE_REQUESTS = [
    "Make me {cuisine} food.",
    "I want to cook {cuisine} cuisine.",
    "Give me a {cuisine} recipe.",
    "I'm craving {cuisine} food.",
    "Can you suggest a {cuisine} dish?",
    "I want something {cuisine}.",
    "{cuisine} recipe please.",
]

REQUESTED_VARIATIONS = [
    "I'd like to use {requested}.",
    "I want to cook with {requested}.",
    "Make something with {requested}.",
    "Can you use {requested}?",
    "I want to use {requested}.",
]


def format_list(items: list) -> str:
    """Format list to natural language (e.g., 'a, b, and c')."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def generate_natural_language(input_data: Dict, scenario: str) -> str:
    """Generate natural language user request based on scenario."""

    inventory = input_data.get('user_inventory', [])
    requested = input_data.get('requested_ingredients')
    preference = input_data.get('preference')
    cuisine = input_data.get('cuisine')

    # Base: inventory
    inventory_str = format_list(inventory)
    text = f"I have {inventory_str}."

    # Scenario 1: Just inventory
    if scenario == "scenario_1":
        request = random.choice(SCENARIO_1_REQUESTS)
        text += f" {request}"
        return text

    # Scenario 2: Inventory + Preference
    if scenario == "scenario_2":
        if preference and preference in PREFERENCE_REQUESTS:
            pref_request = random.choice(PREFERENCE_REQUESTS[preference])
            text += f" {pref_request}"
        return text

    # Scenario 3: Inventory + Cuisine
    if scenario == "scenario_3":
        if cuisine:
            cuisine_template = random.choice(CUISINE_REQUESTS)
            cuisine_request = cuisine_template.format(cuisine=cuisine)
            text += f" {cuisine_request}"
        return text

    # Scenario 4: Inventory + Preference + Cuisine
    if scenario == "scenario_4":
        parts = []
        if preference and preference in PREFERENCE_REQUESTS:
            pref_request = random.choice(PREFERENCE_REQUESTS[preference])
            parts.append(pref_request)
        if cuisine:
            parts.append(f"{cuisine} style.")

        if parts:
            text += f" {' '.join(parts)}"
        return text

    # Scenario 5 & 6: Requested ingredients
    if scenario in ["scenario_5", "scenario_6"]:
        if requested:
            requested_str = format_list(requested)
            requested_template = random.choice(REQUESTED_VARIATIONS)
            requested_text = requested_template.format(requested=requested_str)
            text += f" {requested_text}"

        # Add preference only if present (violations already cleaned)
        if preference and preference in PREFERENCE_REQUESTS:
            pref_request = random.choice(PREFERENCE_REQUESTS[preference])
            text += f" {pref_request}"

        # Add cuisine if present
        if cuisine:
            text += f" {cuisine} style."

        return text

    return text


def convert_to_chatml(data: Dict) -> Dict:
    """Convert a single recipe data to ChatML format."""

    input_data = data['input']
    output_data = data['output']
    scenario = data.get('scenario', 'unknown')

    # Generate natural language user request
    user_message = generate_natural_language(input_data, scenario)

    # System prompt
    system_prompt = "You are a recipe generation AI that creates recipes based on user inventory and preferences."

    # Assistant response (JSON output)
    assistant_response = json.dumps(output_data, ensure_ascii=False)

    # ChatML format
    chatml_text = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_message}<|im_end|>
<|im_start|>assistant
{assistant_response}<|im_end|>"""

    return {
        "text": chatml_text,
        "scenario": scenario,
        "user_message": user_message,
    }


def convert_dataset(input_path: str, output_path: str) -> Dict:
    """Convert entire dataset to ChatML format."""

    converted = []
    stats = {
        'total': 0,
        'by_scenario': {},
    }

    print(f"Converting: {input_path}")

    with open(input_path, 'r') as f:
        for line in f:
            data = json.loads(line.strip())

            # Convert to ChatML
            chatml_data = convert_to_chatml(data)
            converted.append(chatml_data)

            # Stats
            stats['total'] += 1
            scenario = chatml_data['scenario']
            if scenario not in stats['by_scenario']:
                stats['by_scenario'][scenario] = 0
            stats['by_scenario'][scenario] += 1

    # Save converted data
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"  Converted: {stats['total']} recipes")
    print(f"  Saved to: {output_path}")

    return stats


def main():
    """Convert all cleaned datasets to ChatML format."""

    datasets = [
        ('data/synthetic/processed/recipes_train_cleaned.jsonl',
         'data/synthetic/processed/recipes_train_chat.jsonl'),
        ('data/synthetic/processed/recipes_val_cleaned.jsonl',
         'data/synthetic/processed/recipes_val_chat.jsonl'),
        ('data/synthetic/processed/recipes_test_cleaned.jsonl',
         'data/synthetic/processed/recipes_test_chat.jsonl'),
    ]

    print("🔄 Converting datasets to ChatML format...\n")

    all_stats = []

    for input_path, output_path in datasets:
        if not Path(input_path).exists():
            print(f"⚠️  Skipping {input_path} (not found)\n")
            continue

        stats = convert_dataset(input_path, output_path)
        all_stats.append(stats)
        print()

    # Summary
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    total_converted = sum(s['total'] for s in all_stats)
    print(f"Total recipes converted: {total_converted}")

    # Scenario distribution
    scenario_totals = {}
    for stats in all_stats:
        for scenario, count in stats['by_scenario'].items():
            if scenario not in scenario_totals:
                scenario_totals[scenario] = 0
            scenario_totals[scenario] += count

    print("\nScenario distribution:")
    for scenario in sorted(scenario_totals.keys()):
        count = scenario_totals[scenario]
        print(f"  {scenario}: {count}")

    print(f"\n✅ All datasets converted to ChatML format!")


if __name__ == "__main__":
    main()
