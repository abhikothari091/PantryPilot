import re
from difflib import SequenceMatcher

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
    Handles prefixes, parentheticals, and inline numbers.
    """
    text = str(ingredient_text).strip()

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

    # Leading qty/unit: "2 lbs chicken breast"
    prefix = re.search(r"^\s*([\d\.\/]+)\s*([a-zA-Z]+)?\s+(.*)", text)
    if prefix:
        qty_str, unit_str, name_str = prefix.groups()
        qty = parse_qty(qty_str)
        unit = normalize_unit(unit_str) or unit
        if unit_str and normalize_unit(unit_str) is None:
            name_str = f"{unit_str} {name_str}"
            unit = "pcs"
        return qty, unit, name_str.strip()

    # Parenthetical qty/unit after name: "Chicken Breast (4 oz, sliced)"
    paren = re.search(r"^(?P<name>[^()]+)\(\s*(?P<qty>[\d\.\/]+)\s*(?P<unit>[a-zA-Z]+)", text)
    if paren:
        name_str = paren.group("name").strip()
        qty = parse_qty(paren.group("qty"))
        unit = normalize_unit(paren.group("unit")) or unit
        return qty, unit, name_str.strip()

    # Inline number/unit anywhere: "Chicken Breast 4 oz cut"
    inline = re.search(r"([\d\.\/]+)\s*([a-zA-Z]+)", text)
    if inline:
        qty = parse_qty(inline.group(1))
        unit = normalize_unit(inline.group(2)) or unit

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

def norm_text(s: str):
    return re.sub(r"[^a-z0-9\s]", " ", str(s).lower()).strip()


def similarity(a: str, b: str) -> float:
    a_norm = norm_text(a)
    b_norm = norm_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def is_match(inventory_name, ingredient_name, token_threshold: float = 0.45) -> bool:
    """
    Fuzzy match between inventory item and ingredient name.
    """
    a_norm = norm_text(inventory_name)
    b_norm = norm_text(ingredient_name)
    if not a_norm or not b_norm:
        return False

    # Token overlap
    a_tokens = set(a_norm.split())
    b_tokens = set(b_norm.split())
    overlap = a_tokens.intersection(b_tokens)
    if overlap:
        return True

    # Similarity score
    return similarity(a_norm, b_norm) >= token_threshold


def find_best_inventory_match(inventory_items, ingredient_name, min_score: float = 0.45):
    best = None
    best_score = 0.0
    ing_norm = norm_text(ingredient_name)
    for item in inventory_items:
        score = similarity(item.item_name, ing_norm)
        if score > best_score:
            best_score = score
            best = item
    if best_score >= min_score:
        return best, best_score
    return None, 0.0
