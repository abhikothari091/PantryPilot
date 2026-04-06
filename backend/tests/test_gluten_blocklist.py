"""
Tests for hidden-gluten blocklist injection into the LLM system prompt.

Acceptance criteria verified:
- Blocklist is injected when dietary profile is gluten-free.
- Blocklist is absent when dietary profile is not gluten-free.
- Blocklist contains minimum 10 documented hidden-gluten sources.
"""

import pytest

from app.recipe.gluten_blocklist import (
    HIDDEN_GLUTEN_BLOCKLIST,
    build_gluten_free_constraint,
    is_gluten_free_profile,
)
from app.recipe.prompt_builder import build_system_prompt


# ---------------------------------------------------------------------------
# Blocklist content tests
# ---------------------------------------------------------------------------

class TestHiddenGlutenBlocklist:
    """Tests for the static blocklist definition."""

    def test_blocklist_has_minimum_ten_items(self):
        """Blocklist must contain at least 10 hidden-gluten sources."""
        assert len(HIDDEN_GLUTEN_BLOCKLIST) >= 10, (
            f"Expected at least 10 items, got {len(HIDDEN_GLUTEN_BLOCKLIST)}"
        )

    def test_blocklist_contains_highest_frequency_offenders(self):
        """Verify the most commonly encountered hidden-gluten ingredients are present."""
        required = [
            "soy sauce",
            "wheat starch",
            "malt vinegar",
            "barley malt",
            "regular oats",
            "seitan",
            "teriyaki sauce",
        ]
        for item in required:
            assert item in HIDDEN_GLUTEN_BLOCKLIST, (
                f"Expected '{item}' to be in the hidden-gluten blocklist"
            )

    def test_blocklist_items_are_lowercase(self):
        """All blocklist items should be lowercase for case-insensitive matching."""
        for item in HIDDEN_GLUTEN_BLOCKLIST:
            assert item == item.lower(), (
                f"Blocklist item '{item}' should be lowercase"
            )

    def test_blocklist_items_are_non_empty_strings(self):
        """All blocklist items should be non-empty strings."""
        for item in HIDDEN_GLUTEN_BLOCKLIST:
            assert isinstance(item, str) and item.strip(), (
                f"Blocklist item {item!r} is not a valid non-empty string"
            )


# ---------------------------------------------------------------------------
# is_gluten_free_profile tests
# ---------------------------------------------------------------------------

class TestIsGlutenFreeProfile:
    """Tests for dietary preference detection."""

    @pytest.mark.parametrize("preference", [
        "gluten-free",
        "Gluten-Free",
        "GLUTEN-FREE",
        "gluten_free",
        "Gluten_Free",
    ])
    def test_detects_gluten_free_variants(self, preference: str):
        assert is_gluten_free_profile(preference) is True

    @pytest.mark.parametrize("preference", [
        "vegan",
        "vegetarian",
        "dairy-free",
        "non-veg",
        "none",
        "",
        None,
        "keto",
    ])
    def test_rejects_non_gluten_free_profiles(self, preference):
        assert is_gluten_free_profile(preference) is False


# ---------------------------------------------------------------------------
# build_gluten_free_constraint tests
# ---------------------------------------------------------------------------

class TestBuildGlutenFreeConstraint:
    """Tests for the constraint string builder."""

    def test_constraint_contains_all_blocklist_items(self):
        constraint = build_gluten_free_constraint()
        for item in HIDDEN_GLUTEN_BLOCKLIST:
            assert item in constraint, (
                f"Expected constraint to mention '{item}'"
            )

    def test_constraint_is_non_empty_string(self):
        constraint = build_gluten_free_constraint()
        assert isinstance(constraint, str) and constraint.strip()

    def test_constraint_contains_celiac_keyword(self):
        """Constraint should clearly indicate celiac/gluten-free severity."""
        constraint = build_gluten_free_constraint()
        assert "celiac" in constraint.lower() or "gluten-free" in constraint.lower()


# ---------------------------------------------------------------------------
# build_system_prompt injection tests  (primary acceptance criteria)
# ---------------------------------------------------------------------------

class TestSystemPromptInjection:
    """Tests verifying blocklist injection logic in the system prompt builder."""

    def test_blocklist_injected_when_gluten_free(self):
        """
        AC: Blocklist constraint is present in system prompt for gluten-free profile.
        """
        prompt = build_system_prompt(dietary_preference="gluten-free")

        # The full blocklist constraint must be present
        for item in HIDDEN_GLUTEN_BLOCKLIST:
            assert item in prompt, (
                f"Expected system prompt to contain blocked ingredient '{item}' "
                f"for gluten-free profile"
            )

        # Explicit constraint header must be present
        assert "GLUTEN-FREE CONSTRAINT" in prompt

    def test_blocklist_absent_when_not_gluten_free(self):
        """
        AC: Blocklist constraint is absent from system prompt for non-gluten-free profiles.
        """
        for preference in ["vegan", "vegetarian", "dairy-free", "none", None]:
            prompt = build_system_prompt(dietary_preference=preference)
            assert "GLUTEN-FREE CONSTRAINT" not in prompt, (
                f"Did not expect gluten-free constraint for preference={preference!r}"
            )
            # Spot-check: seitan should not appear in non-GF prompts
            assert "seitan" not in prompt, (
                f"Did not expect 'seitan' in prompt for preference={preference!r}"
            )

    def test_blocklist_injected_case_insensitive_variants(self):
        """Gluten-free detection should work for common casing variants."""
        for preference in ["Gluten-Free", "GLUTEN-FREE", "gluten_free"]:
            prompt = build_system_prompt(dietary_preference=preference)
            assert "GLUTEN-FREE CONSTRAINT" in prompt, (
                f"Expected injection for preference={preference!r}"
            )

    def test_base_prompt_content_preserved_for_gluten_free(self):
        """Base system prompt content should remain intact when constraint is injected."""
        prompt = build_system_prompt(dietary_preference="gluten-free")
        assert "RecipeGen" in prompt
        assert "culinary_preference" in prompt
        assert "shopping_list" in prompt

    def test_base_prompt_content_preserved_without_constraint(self):
        """Base system prompt content should remain intact without constraint."""
        prompt = build_system_prompt(dietary_preference="vegan")
        assert "RecipeGen" in prompt
        assert "culinary_preference" in prompt
        assert "shopping_list" in prompt

    def test_prompt_is_string(self):
        """build_system_prompt must always return a string."""
        assert isinstance(build_system_prompt("gluten-free"), str)
        assert isinstance(build_system_prompt("vegan"), str)
        assert isinstance(build_system_prompt(None), str)

    def test_minimum_blocklist_size_via_prompt(self):
        """
        AC: Blocklist contains minimum 10 documented hidden-gluten sources.
        Verify by counting how many blocklist items appear in the injected prompt.
        """
        prompt = build_system_prompt(dietary_preference="gluten-free")
        found = [item for item in HIDDEN_GLUTEN_BLOCKLIST if item in prompt]
        assert len(found) >= 10, (
            f"Expected at least 10 blocklist items in prompt, found {len(found)}: {found}"
        )
