"""
Generate 15,000 synthetic recipes using Groq API (Llama 3.1 8B).
Implements 6 scenarios with parallel processing and rate limiting.
"""

import os
import sys
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml
from groq import Groq
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.ingredient_pools import (
    get_cuisine_ingredients,
    get_preference_compatible_ingredients,
    get_random_inventory,
    CUISINE_INGREDIENTS,
    COMMON_INGREDIENTS,
    PREFERENCE_ALLOWED,
)
from utils.prompt_templates import create_prompt_for_scenario


class RecipeGenerator:
    """Generate synthetic recipes using Groq API."""

    def __init__(self, config_path: str, api_key: str):
        """Initialize generator with config and API key."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.client = Groq(api_key=api_key)
        self.model = self.config['groq']['model']
        self.temperature = self.config['groq']['temperature']
        self.max_tokens = self.config['groq']['max_tokens']
        self.rate_limit = self.config['groq']['rate_limit']
        self.batch_size = self.config['groq']['batch_size']
        self.max_retries = self.config['groq']['max_retries']

        self.cuisines = self.config['cuisines']
        self.preferences = self.config['preferences']

        # Statistics
        self.stats = {
            'total_generated': 0,
            'total_failed': 0,
            'scenario_counts': {},
            'start_time': None,
            'end_time': None,
        }

    def generate_single_recipe(self, scenario_data: dict) -> Optional[dict]:
        """Generate a single recipe using Groq API."""
        from utils.prompt_templates import create_prompt_for_scenario

        prompt = create_prompt_for_scenario(scenario_data)

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"}
                )

                # Parse JSON response
                content = response.choices[0].message.content
                output_data = json.loads(content)

                # Construct full data point
                result = {
                    "input": {
                        "user_inventory": scenario_data["inventory"],
                        "requested_ingredients": scenario_data.get("requested_ingredients"),
                        "user_request": scenario_data.get("user_request", ""),
                        "preference": scenario_data.get("preference"),
                        "cuisine": scenario_data.get("cuisine"),
                    },
                    "output": output_data,
                    "scenario": scenario_data["scenario"],
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                }

                return result

            except json.JSONDecodeError as e:
                print(f"JSON decode error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)

            except Exception as e:
                print(f"Error generating recipe (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)

        return None

    def create_scenario_1_data(self, count: int, subtype: str) -> List[dict]:
        """Create data for Scenario 1: Full inventory usage."""
        scenarios = []

        for _ in range(count):
            if subtype == "cultural_specific":
                # Use cuisine-specific ingredients
                cuisine = random.choice(self.cuisines)
                inventory = get_cuisine_ingredients(cuisine, random.randint(5, 8))
            elif subtype == "neutral":
                # Use common ingredients
                inventory = random.sample(COMMON_INGREDIENTS, random.randint(4, 7))
            else:  # fusion
                # Mix ingredients from different cuisines
                cuisine1, cuisine2 = random.sample(self.cuisines, 2)
                inv1 = get_cuisine_ingredients(cuisine1, 3)
                inv2 = get_cuisine_ingredients(cuisine2, 3)
                inventory = inv1 + inv2

            scenarios.append({
                "scenario": "scenario_1",
                "inventory": inventory,
                "subtype": subtype,
            })

        return scenarios

    def create_scenario_2_data(self, preference_distribution: dict) -> List[dict]:
        """Create data for Scenario 2: Inventory + preference."""
        scenarios = []

        for preference, count in preference_distribution.items():
            for _ in range(count):
                inventory = get_preference_compatible_ingredients(preference, random.randint(5, 8))

                scenarios.append({
                    "scenario": "scenario_2",
                    "inventory": inventory,
                    "preference": preference,
                })

        return scenarios

    def create_scenario_3_data(self, cuisine_distribution: dict) -> List[dict]:
        """Create data for Scenario 3: Inventory + cuisine."""
        scenarios = []

        for cuisine, count in cuisine_distribution.items():
            for _ in range(count):
                inventory = get_cuisine_ingredients(cuisine, random.randint(5, 8))

                scenarios.append({
                    "scenario": "scenario_3",
                    "inventory": inventory,
                    "cuisine": cuisine,
                })

        return scenarios

    def create_scenario_4_data(self, count: int) -> List[dict]:
        """Create data for Scenario 4: All specified (cuisine + preference)."""
        scenarios = []

        for _ in range(count):
            cuisine = random.choice(self.cuisines)
            preference = random.choice(self.preferences)

            # Get compatible ingredients
            inventory = get_preference_compatible_ingredients(preference, random.randint(5, 8))

            scenarios.append({
                "scenario": "scenario_4",
                "inventory": inventory,
                "preference": preference,
                "cuisine": cuisine,
            })

        return scenarios

    def create_scenario_5_data(self, count: int) -> List[dict]:
        """Create data for Scenario 5: Specific ingredients - all available."""
        scenarios = []

        for _ in range(count):
            # Create inventory
            inventory = get_random_inventory(6, 10)

            # Request 2-4 ingredients from inventory
            num_requested = random.randint(2, 4)
            requested = random.sample(inventory, min(num_requested, len(inventory)))

            # Randomly add preference/cuisine
            preference = random.choice([None] + self.preferences) if random.random() < 0.3 else None
            cuisine = random.choice([None] + self.cuisines) if random.random() < 0.3 else None

            scenarios.append({
                "scenario": "scenario_5",
                "inventory": inventory,
                "requested_ingredients": requested,
                "preference": preference,
                "cuisine": cuisine,
            })

        return scenarios

    def create_scenario_6_data(self, partial_count: int, no_match_count: int) -> List[dict]:
        """Create data for Scenario 6: Specific ingredients - some/all missing."""
        scenarios = []

        # Partial match (some missing)
        for _ in range(partial_count):
            inventory = get_random_inventory(5, 8)

            # Request 3-5 ingredients, some not in inventory
            num_requested = random.randint(3, 5)
            num_available = random.randint(1, num_requested - 1)  # At least one missing

            available = random.sample(inventory, min(num_available, len(inventory)))
            missing = random.sample(COMMON_INGREDIENTS, num_requested - num_available)
            # Filter out items already in inventory
            missing = [m for m in missing if m not in inventory][:num_requested - num_available]

            requested = available + missing

            scenarios.append({
                "scenario": "scenario_6",
                "inventory": inventory,
                "requested_ingredients": requested,
                "missing_ingredients": missing,
            })

        # No match (all missing)
        for _ in range(no_match_count):
            inventory = get_random_inventory(5, 8)

            # Request ingredients NOT in inventory
            num_requested = random.randint(2, 4)
            missing = random.sample(COMMON_INGREDIENTS, num_requested * 2)
            missing = [m for m in missing if m not in inventory][:num_requested]

            scenarios.append({
                "scenario": "scenario_6",
                "inventory": inventory,
                "requested_ingredients": missing,
                "missing_ingredients": missing,
            })

        return scenarios

    def create_all_scenarios(self) -> List[dict]:
        """Create all 12,000 training scenarios."""
        all_scenarios = []

        # Scenario 1: 3000
        print("Creating Scenario 1 data...")
        all_scenarios.extend(self.create_scenario_1_data(2100, "cultural_specific"))
        all_scenarios.extend(self.create_scenario_1_data(600, "neutral"))
        all_scenarios.extend(self.create_scenario_1_data(300, "fusion"))

        # Scenario 2: 2400
        print("Creating Scenario 2 data...")
        pref_dist = self.config['scenarios']['scenario_2']['distribution']
        all_scenarios.extend(self.create_scenario_2_data(pref_dist))

        # Scenario 3: 1800
        print("Creating Scenario 3 data...")
        cuisine_dist = self.config['scenarios']['scenario_3']['distribution']
        all_scenarios.extend(self.create_scenario_3_data(cuisine_dist))

        # Scenario 4: 1200
        print("Creating Scenario 4 data...")
        all_scenarios.extend(self.create_scenario_4_data(1200))

        # Scenario 5: 2400
        print("Creating Scenario 5 data...")
        all_scenarios.extend(self.create_scenario_5_data(2400))

        # Scenario 6: 1200 (900 partial + 300 no match)
        print("Creating Scenario 6 data...")
        all_scenarios.extend(self.create_scenario_6_data(900, 300))

        # Shuffle
        random.shuffle(all_scenarios)

        print(f"Total scenarios created: {len(all_scenarios)}")
        return all_scenarios

    def generate_batch(self, scenarios: List[dict]) -> List[dict]:
        """Generate a batch of recipes with parallel processing."""
        results = []

        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            futures = {executor.submit(self.generate_single_recipe, s): s for s in scenarios}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    self.stats['total_generated'] += 1
                else:
                    self.stats['total_failed'] += 1

        return results

    def generate_all_recipes(self, output_path: str):
        """Generate all 12,000 recipes with progress tracking."""
        print("Generating all scenario data...")
        all_scenarios = self.create_all_scenarios()

        print(f"\nStarting generation of {len(all_scenarios)} recipes...")
        print(f"Rate limit: {self.rate_limit} requests/min")
        print(f"Batch size: {self.batch_size}")
        print(f"Estimated time: {len(all_scenarios) / self.rate_limit:.1f} minutes\n")

        self.stats['start_time'] = datetime.utcnow().isoformat()

        all_results = []
        batch_start_time = time.time()

        # Process in batches
        for i in tqdm(range(0, len(all_scenarios), self.batch_size), desc="Generating recipes"):
            batch = all_scenarios[i:i + self.batch_size]

            # Generate batch
            results = self.generate_batch(batch)
            all_results.extend(results)

            # Save incrementally every 100 recipes
            if len(all_results) % 100 == 0:
                self.save_results(all_results, output_path)

            # Rate limiting: ensure we don't exceed rate_limit per minute
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time

            if batch_duration < 60:  # If batch took less than 1 minute
                sleep_time = 60 - batch_duration
                time.sleep(sleep_time)

            batch_start_time = time.time()

        # Final save
        self.save_results(all_results, output_path)

        self.stats['end_time'] = datetime.utcnow().isoformat()

        # Save statistics
        stats_path = self.config['paths']['stats_report']
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)

        print(f"\n✅ Generation complete!")
        print(f"Total generated: {self.stats['total_generated']}")
        print(f"Total failed: {self.stats['total_failed']}")
        print(f"Success rate: {self.stats['total_generated'] / len(all_scenarios) * 100:.2f}%")
        print(f"Results saved to: {output_path}")
        print(f"Statistics saved to: {stats_path}")

    def save_results(self, results: List[dict], output_path: str):
        """Save results to JSONL file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            for result in results:
                f.write(json.dumps(result) + '\n')


def main():
    """Main execution."""
    # Get API key from environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY environment variable not set!")
        print("Set it with: export GROQ_API_KEY='your-api-key'")
        sys.exit(1)

    # Paths
    config_path = "config/synthetic_recipe_config.yaml"
    output_path = "data/synthetic/raw/recipes_15k_raw.jsonl"

    # Check config exists
    if not os.path.exists(config_path):
        print(f"❌ Error: Config file not found at {config_path}")
        sys.exit(1)

    # Initialize generator
    print("🚀 Initializing Recipe Generator...")
    generator = RecipeGenerator(config_path, api_key)

    # Generate all recipes
    generator.generate_all_recipes(output_path)


if __name__ == "__main__":
    main()
