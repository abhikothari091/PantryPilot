import pytest

from app.services.recipe_validation import (
    SAFE_FALLBACK_RESPONSE,
    find_blocklist_violations,
    generate_with_validation,
)

# ---------------------------------------------------------------------------
# find_blocklist_violations
# ---------------------------------------------------------------------------

GLUTEN_PROMPTS_CLEAN = [
    "Stir fry the chicken with olive oil and garlic.",
    "Mix coconut aminos with lime juice.",
    "Add rice noodles, tofu, and scallions.",
    "Grill salmon with lemon and capers.",
    "Combine black beans, corn, and cilantro.",
    "Steam broccoli until tender, season with salt.",
    "Scramble eggs with spinach and feta.",
    "Roast sweet potato wedges with paprika.",
    "Blend mango, banana, and almond milk.",
    "Toss quinoa with cherry tomatoes and basil.",
]

GLUTEN_PROMPTS_DIRTY = [
    ("Marinate chicken in soy sauce and ginger.", "soy sauce"),
    ("Add a splash of malt vinegar to the dressing.", "malt vinegar"),
    ("Coat the beef in wheat starch before frying.", "wheat starch"),
    ("Use barley malt syrup to sweeten the glaze.", "barley malt"),
    ("Serve seitan strips over noodles.", "seitan"),
    ("Brush with teriyaki sauce before grilling.", "teriyaki sauce"),
    ("Toast regular oats and mix with honey.", "regular oats"),
    ("Stir in soy sauce to deepen the umami.", "soy sauce"),
    ("Drizzle malt vinegar over the chips.", "malt vinegar"),
    ("Use wheat starch to thicken the gravy.", "wheat starch"),
    ("Sweeten with barley malt extract.", "barley malt"),
    ("Pan-fry the seitan with mushrooms.", "seitan"),
    ("Glaze with teriyaki sauce before serving.", "teriyaki sauce"),
    ("Mix regular oats into the batter.", "regular oats"),
    ("Add Soy Sauce (uppercase) to the marinade.", "soy sauce"),
    ("Include WHEAT STARCH in the coating.", "wheat starch"),
    ("The recipe uses Malt Vinegar for tang.", "malt vinegar"),
    ("Combine Barley Malt with water.", "barley malt"),
    ("Serve with SEITAN on the side.", "seitan"),
    ("Brush Teriyaki Sauce over the skewers.", "teriyaki sauce"),
    ("Top with Regular Oats for crunch.", "regular oats"),
]


@pytest.mark.parametrize("text", GLUTEN_PROMPTS_CLEAN)
def test_find_violations_returns_empty_for_clean_recipes(text):
    assert find_blocklist_violations(text) == []


@pytest.mark.parametrize("text,expected_ingredient", GLUTEN_PROMPTS_DIRTY)
def test_find_violations_catches_every_blocklisted_ingredient(text, expected_ingredient):
    violations = find_blocklist_violations(text)
    assert expected_ingredient in violations, (
        f"Expected '{expected_ingredient}' to be flagged in: {text!r}"
    )


# ---------------------------------------------------------------------------
# generate_with_validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clean_recipe_returned_directly():
    async def mock_llm(prompt):
        return "Grill chicken with lemon and herbs."

    result = await generate_with_validation(mock_llm, "Make a quick chicken dish.", None)
    assert result["recipe"] == "Grill chicken with lemon and herbs."
    assert "error" not in result


@pytest.mark.asyncio
async def test_retry_triggered_and_clean_retry_returned():
    calls = []

    async def mock_llm(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return "Marinate in soy sauce and grill."
        return "Marinate in coconut aminos and grill."

    result = await generate_with_validation(mock_llm, "Make a quick chicken dish.", None)
    assert len(calls) == 2
    assert result["recipe"] == "Marinate in coconut aminos and grill."
    assert "error" not in result


@pytest.mark.asyncio
async def test_safe_fallback_returned_when_retry_also_violates():
    async def mock_llm(prompt):
        return "Marinate in soy sauce and malt vinegar."

    result = await generate_with_validation(mock_llm, "Make a quick chicken dish.", None)
    assert result == SAFE_FALLBACK_RESPONSE
    assert result["recipe"] is None
    assert result["error"] == "recipe_constraint_violation"


@pytest.mark.asyncio
async def test_no_blocked_recipe_ever_returned_to_client():
    """Exhaustive check: none of the dirty prompts produce a recipe key with blocked content."""

    async def always_violating_llm(prompt):
        return "Use soy sauce and wheat starch to coat the protein."

    for text, _ in GLUTEN_PROMPTS_DIRTY:
        result = await generate_with_validation(always_violating_llm, text, None)
        assert result["recipe"] is None, (
            f"Blocked recipe was returned for prompt: {text!r}"
        )
