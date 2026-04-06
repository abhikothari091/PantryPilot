"""
Hidden-gluten ingredient blocklist for celiac/gluten-free dietary profiles.

This module defines a static list of ingredients that contain hidden gluten
and are commonly overlooked. When a user's dietary profile is gluten-free,
this blocklist is injected into the LLM system prompt as an explicit constraint.
"""

from typing import List

# Minimum 10 documented hidden-gluten sources covering highest-frequency offenders.
# Each entry is a lowercase string for case-insensitive matching.
HIDDEN_GLUTEN_BLOCKLIST: List[str] = [
    "soy sauce",           # contains wheat; use tamari as GF alternative
    "wheat starch",        # direct wheat derivative
    "malt vinegar",        # derived from barley
    "barley malt",         # barley-based; often in cereals and beers
    "regular oats",        # cross-contaminated unless certified GF
    "seitan",              # literally wheat gluten
    "teriyaki sauce",      # typically contains soy sauce (wheat)
    "hoisin sauce",        # usually contains wheat flour
    "oyster sauce",        # commonly thickened with wheat starch
    "worcestershire sauce", # traditionally contains malt vinegar (barley)
    "bulgur",              # wheat grain
    "farro",               # ancient wheat grain
    "spelt",               # wheat variety
    "kamut",               # wheat variety
    "triticale",           # wheat-rye hybrid
    "couscous",            # made from semolina (wheat)
    "semolina",            # wheat product
    "durum wheat",         # pasta wheat
    "wheat flour",         # direct gluten source
    "panko breadcrumbs",   # typically made from wheat bread
]


GLUTEN_FREE_CONSTRAINT_TEMPLATE = (
    "GLUTEN-FREE CONSTRAINT (STRICT - user has celiac disease):\n"
    "The following ingredients contain hidden gluten and MUST NOT appear "
    "in the recipe under any circumstances:\n"
    "{blocklist_items}\n"
    "Do NOT use any of these ingredients or any product that typically contains them. "
    "Substitute soy sauce with tamari or coconut aminos, use certified gluten-free oats "
    "if oats are needed, and verify all sauces and condiments are explicitly gluten-free."
)


def build_gluten_free_constraint() -> str:
    """
    Build the gluten-free constraint string to inject into the LLM system prompt.

    Returns a formatted string listing all hidden-gluten blocklist items
    as an explicit constraint for the LLM.
    """
    blocklist_items = "\n".join(
        f"  - {item}" for item in HIDDEN_GLUTEN_BLOCKLIST
    )
    return GLUTEN_FREE_CONSTRAINT_TEMPLATE.format(blocklist_items=blocklist_items)


def is_gluten_free_profile(dietary_preference: str) -> bool:
    """
    Check whether the dietary preference string indicates a gluten-free profile.

    Args:
        dietary_preference: The user's dietary preference string.

    Returns:
        True if the profile is gluten-free, False otherwise.
    """
    if not dietary_preference:
        return False
    return "gluten-free" in dietary_preference.lower().replace("_", "-")
