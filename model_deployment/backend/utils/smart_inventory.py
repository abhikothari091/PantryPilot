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
             "Chicken Breast (4 oz, sliced)" -> (4.0, "oz", "Chicken Breast")
    """
    text = ingredient_text.strip()

    # Pattern: leading quantity/unit before the name
    pattern_prefix = r"([\d\.\/]+)\s*([a-zA-Z]+)?\s+(.*)"
    match = re.search(pattern_prefix, text)

    qty = 1.0
    unit = "pcs"
    name_str = text

    def parse_qty(qs):
        try:
            if "/" in qs:
                num, den = map(float, qs.split("/"))
                return num / den
            return float(qs)
        except Exception:
            return 1.0

    if match:
        qty_str, unit_str, name_str = match.groups()
        qty = parse_qty(qty_str)
        unit = normalize_unit(unit_str) or unit
        if unit_str and normalize_unit(unit_str) is None:
            name_str = f"{unit_str} {name_str}"
            unit = "pcs"
        name_str = name_str.strip()
    else:
        # Pattern: name first, quantity/unit in parentheses: "Chicken Breast (4 oz, ...)"
        paren = re.search(r"^(?P<name>[^()]+)\(\s*(?P<qty>[\d\.\/]+)\s*(?P<unit>[a-zA-Z]+)", text)
        if paren:
            name_str = paren.group("name").strip()
            qty = parse_qty(paren.group("qty"))
            unit = normalize_unit(paren.group("unit")) or unit

    return qty, unit, name_str.strip()

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
