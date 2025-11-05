from pint import UnitRegistry

ureg = UnitRegistry()
ureg.define("pcs = 1 count")

def to_canonical(qty, unit):
    """Convert quantity and unit to a canonical unit (grams, milliliters, or pieces)."""
    try:
        if unit in ["kg", "g"]:
            return (qty * ureg(unit)).to("g").magnitude, "g"
        elif unit in ["L", "ml"]:
            return (qty * ureg(unit)).to("ml").magnitude, "ml"
        elif unit == "pcs":
            return qty, "pcs"
    except Exception:
        return qty, unit
    return qty, unit