import re

# Standard Unit Mappings
UNIT_MAPPINGS = {
    # Weight
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",
    
    # Volume
    "cup": "cup", "cups": "cup",
    "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "l": "l", "liter": "l", "liters": "l",
    "fl oz": "fl oz", "fluid ounce": "fl oz",
    
    # Count
    "pc": "pcs", "pcs": "pcs", "piece": "pcs", "pieces": "pcs",
    "unit": "pcs", "units": "pcs",
    "can": "can", "cans": "can",
    "bunch": "bunch", "bunches": "bunch",
    "head": "head", "heads": "head",
    "clove": "clove", "cloves": "clove"
}

# Conversion Factors (to base unit)
# Weight Base: g
WEIGHT_TO_G = {
    "g": 1,
    "kg": 1000,
    "lb": 453.592,
    "oz": 28.3495
}

# Volume Base: ml
VOLUME_TO_ML = {
    "ml": 1,
    "l": 1000,
    "cup": 236.588,
    "tbsp": 14.7868,
    "tsp": 4.92892,
    "fl oz": 29.5735
}

def normalize_unit(unit_str):
    """Normalize unit string to standard key (e.g. 'pounds' -> 'lb')"""
    if not unit_str:
        return None
    return UNIT_MAPPINGS.get(unit_str.lower().strip(), unit_str.lower().strip())

def parse_ingredient(ingredient_text):
    """
    Parse ingredient string into (quantity, unit, name)
    Example: "2 lbs Chicken Breast" -> (2.0, "lb", "Chicken Breast")
    """
    # Regex for "Number Unit Name" or "Number Name"
    # Handles fractions (1/2) and decimals (1.5)
    pattern = r"([\d\.\/]+)\s*([a-zA-Z]+)?\s+(.*)"
    match = re.search(pattern, ingredient_text)
    
    if match:
        qty_str, unit_str, name_str = match.groups()
        
        # Parse quantity
        try:
            if '/' in qty_str:
                num, den = map(float, qty_str.split('/'))
                qty = num / den
            else:
                qty = float(qty_str)
        except:
            qty = 1.0 # Default if parse fails
            
        # Normalize unit
        unit = normalize_unit(unit_str)
        
        # If unit is None or not in our map, it might be part of the name
        # e.g. "2 Chicken Breasts" -> unit="Chicken", name="Breasts" (Wrong)
        # Better heuristic: check if unit_str is a known unit
        if unit_str and normalize_unit(unit_str) is None:
            # It's likely part of the name
            name_str = f"{unit_str} {name_str}"
            unit = "pcs" # Default to pieces if no known unit found
            
        return qty, unit, name_str.strip()
    
    return 1.0, "pcs", ingredient_text.strip()

def convert_unit(qty, from_unit, to_unit):
    """
    Convert quantity between units. Returns None if incompatible.
    Example: convert_unit(1, 'lb', 'oz') -> 16.0
    """
    from_u = normalize_unit(from_unit)
    to_u = normalize_unit(to_unit)
    
    if not from_u or not to_u:
        return None
        
    if from_u == to_u:
        return qty
        
    # Weight Conversion
    if from_u in WEIGHT_TO_G and to_u in WEIGHT_TO_G:
        g_val = qty * WEIGHT_TO_G[from_u]
        return g_val / WEIGHT_TO_G[to_u]
        
    # Volume Conversion
    if from_u in VOLUME_TO_ML and to_u in VOLUME_TO_ML:
        ml_val = qty * VOLUME_TO_ML[from_u]
        return ml_val / VOLUME_TO_ML[to_u]
        
    return None

def is_match(inventory_name, ingredient_name):
    """
    Check if inventory item matches ingredient name.
    Handles singular/plural and partial matches.
    """
    inv = inventory_name.lower()
    ing = ingredient_name.lower()
    
    # Exact match
    if inv == ing:
        return True
        
    # Singular/Plural (Simple heuristic)
    if inv + "s" == ing or inv + "es" == ing:
        return True
    if ing + "s" == inv or ing + "es" == inv:
        return True
        
    # Substring match (Inventory in Ingredient)
    # e.g. Inv="Chicken", Ing="Boneless Chicken Breast" -> Match
    # But be careful: Inv="Rice", Ing="Rice Vinegar" -> False Positive?
    # For now, we assume user wants aggressive matching
    if inv in ing:
        return True
        
    # Substring match (Ingredient in Inventory)
    # e.g. Inv="Organic Bananas", Ing="Banana" -> Match
    if ing in inv:
        return True
        
    return False
