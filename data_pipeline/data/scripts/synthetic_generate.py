import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from pathlib import Path

# --------------------------
# CONFIG
# --------------------------
NUM_USERS = 20
ITEMS_PER_USER = 50  # Reduced to avoid sampling error (item pool has 58 items)
PURCHASES_PER_USER = 300
random.seed(42)
np.random.seed(42)

# --------------------------
# Helper functions
# --------------------------
def random_date(start, end):
    """Return a random date between start and end."""
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def random_brand():
    return random.choice(["Kirkland", "365", "Trader Joe's", "Whole Foods", "Great Value", "Organic Farm"])

def random_category():
    return random.choice([
        "grains_cereals", "dairy_eggs", "meat_poultry", "seafood",
        "snacks", "condiments_spices", "beverages", "produce", "frozen_foods"
    ])

def random_unit(category):
    return random.choice(["g", "kg", "ml", "L", "oz", "lb", "pack", "pcs"])

def random_storage(category):
    if category in ["frozen_foods", "meat_poultry", "seafood"]:
        return "freezer"
    elif category in ["produce", "dairy_eggs"]:
        return "refrigerator"
    else:
        return "pantry"

def random_tags(category):
    base_tags = ["organic", "vegan", "gluten_free", "contains_nuts", "low_sugar"]
    return ",".join(random.sample(base_tags, random.randint(0, 3)))

def random_payment():
    return random.choice(["credit_card", "debit_card", "cash", "mobile_pay"])

def random_store():
    return random.choice(["Whole Foods", "Trader Joe's", "Target", "Costco", "Walmart"])

def random_channel():
    return random.choice(["in_store", "online"])

# --------------------------
# Generate Inventory
# --------------------------
inventory_rows = []

for user in range(1, NUM_USERS + 1):
    user_id = f"user_{user:03d}"
    item_names = random.sample([
        "salt", "rice", "milk", "bread", "eggs", "chicken", "apple", "banana", "beef",
        "yogurt", "spinach", "broccoli", "butter", "cheese", "tomato", "potato",
        "carrot", "onion", "flour", "sugar", "coffee", "tea", "juice", "oil",
        "soy_sauce", "vinegar", "pepper", "pasta", "cereal", "chocolate",
        "cookies", "frozen_pizza", "fish", "shrimp", "orange", "strawberry",
        "lettuce", "mushroom", "garlic", "ginger", "tofu", "bacon", "ham",
        "mayonnaise", "mustard", "ketchup", "honey", "jam", "oats", "buttermilk",
        "cream", "chips", "water", "soda", "beer", "wine", "ice_cream", "nuts", "beans"
    ], ITEMS_PER_USER)

    for item in item_names:
        category = random_category()
        expiry = random_date(datetime(2025, 1, 1), datetime(2026, 12, 31))
        allergen_flag = random.choice([True, False])
        unit_cost = round(random.uniform(1.0, 25.0), 2)
        quantity = round(random.uniform(0.5, 5.0), 2)
        inventory_rows.append({
            "user_id": user_id,
            "item_id": f"I_{item}",
            "item_name": item,
            "quantity": quantity,
            "unit": random_unit(category),
            "category": category,
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "allergen_flag": allergen_flag,
            "unit_cost": unit_cost,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "storage_type": random_storage(category),
            "brand": random_brand(),
            "nutritional_tags": random_tags(category),
            "daily_usage_rate": round(random.uniform(0.05, 0.5), 2),
            "reorder_threshold": round(random.uniform(0.3, 2.0), 2),
            "purchase_date": random_date(datetime(2024, 1, 1), datetime(2025, 10, 1)).strftime("%Y-%m-%d"),
            "source": "synthetic_generation"
        })

inventory_df = pd.DataFrame(inventory_rows)

# --------------------------
# Generate Purchase History
# --------------------------
purchase_rows = []

for user in range(1, NUM_USERS + 1):
    user_id = f"user_{user:03d}"
    user_items = inventory_df[inventory_df["user_id"] == user_id]["item_id"].tolist()

    for i in range(PURCHASES_PER_USER):
        item_id = random.choice(user_items)
        item_name = inventory_df[inventory_df["item_id"] == item_id]["item_name"].values[0]
        quantity = round(random.uniform(0.5, 3.0), 2)
        price_total = round(quantity * random.uniform(2.0, 20.0), 2)
        purchase_date = random_date(datetime(2024, 1, 1), datetime(2025, 10, 1))
        purchase_rows.append({
            "user_id": user_id,
            "transaction_id": f"T_{user_id}_{i+1:04d}",
            "item_id": item_id,
            "item_name": item_name,
            "quantity_purchased": quantity,
            "unit": random.choice(["kg", "g", "L", "pcs", "pack"]),
            "price_total": price_total,
            "purchase_date": purchase_date.strftime("%Y-%m-%d"),
            "store_name": random_store(),
            "payment_method": random_payment(),
            "discount_applied": random.choice([True, False]),
            "category": random_category(),
            "brand": random_brand(),
            "location": random.choice(["Boston, MA", "Cambridge, MA", "Somerville, MA", "Brookline, MA"]),
            "receipt_source": random.choice(["in_app", "manual_entry", "photo_scan"]),
            "weekday": purchase_date.strftime("%A"),
            "purchase_channel": random_channel(),
            "consumption_start_date": (purchase_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            "expected_depletion_date": (purchase_date + timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d")
        })

purchase_df = pd.DataFrame(purchase_rows)

# --------------------------
# Export to CSV
# --------------------------
project_root = Path(__file__).resolve().parents[2]
output_dir = project_root / "data" / "synthetic_data"
output_dir.mkdir(parents=True, exist_ok=True)

inventory_path = output_dir / "pantrypilot_inventory_u20_i60_shared_ids.csv"
purchase_path = output_dir / "pantrypilot_purchase_u20_i60_shared_ids.csv"

inventory_df.to_csv(inventory_path, index=False)
purchase_df.to_csv(purchase_path, index=False)

print("✅ Synthetic data generated successfully:")
print(f"Inventory: {inventory_df.shape} rows, Purchase history: {purchase_df.shape} rows")
print(f"Files saved to: {output_dir}")
