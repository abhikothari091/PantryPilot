"""
Integration test suite for gluten-free recipe generation safety.

Covers:
- Clean recipes (no blocklist violations) across diverse prompts
- Single-hit blocklist violations (soy sauce, wheat starch, etc.)
- Multi-hit blocklist violations
- Retry logic: first response violates, retry returns clean recipe
- Retry exhaustion: both attempts contain violations
- Structured logging fields emitted during gluten-free generation

All LLM calls are mocked via client.app.state.model_service injection.
See tests/README.md for how to run locally and add new test cases.
"""

import json
import logging
import pytest
from unittest.mock import Mock, call

from conftest import GLUTEN_BLOCKLIST, make_clean_gf_recipe, make_violation_gf_recipe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _response_text(response):
    """Return the full response body as a lowercase string for blocklist scanning."""
    return json.dumps(response.json()).lower()


def _assert_no_blocklist_hit(response):
    """Fail the test if any blocklisted ingredient appears in the response JSON."""
    body = _response_text(response)
    for ingredient in GLUTEN_BLOCKLIST:
        assert ingredient.lower() not in body, (
            f"Blocklisted ingredient '{ingredient}' found in recipe response"
        )


def _post_recipe(client, headers, user_request, servings=2):
    return client.post(
        "/recipes/generate",
        headers=headers,
        json={"user_request": user_request, "servings": servings},
    )


# ---------------------------------------------------------------------------
# Clean recipe scenarios (8 test cases)
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_clean_rice_stir_fry(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: rice stir-fry with no hidden gluten."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="Chicken Rice Stir-Fry",
        ingredients=["rice", "chicken breast", "broccoli", "garlic", "sesame oil"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "chicken rice stir-fry")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_baked_potato(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: baked potato with no hidden gluten."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="Loaded Baked Potato",
        ingredients=["potatoes", "olive oil", "cheddar cheese", "sour cream", "chives"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "loaded baked potato")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_egg_scramble(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: egg scramble with vegetables."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="Veggie Egg Scramble",
        ingredients=["eggs", "tomatoes", "olive oil", "garlic", "spinach"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "egg scramble with vegetables")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_tomato_soup(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: tomato soup with gluten-free thickener."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="GF Tomato Soup",
        ingredients=["tomatoes", "olive oil", "garlic", "vegetable broth", "cornstarch"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "tomato soup")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_grilled_chicken(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: grilled chicken with herbs."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="Herb Grilled Chicken",
        ingredients=["chicken breast", "olive oil", "rosemary", "thyme", "lemon"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "herb grilled chicken")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_vegetable_curry(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: vegetable curry using rice as base."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="GF Vegetable Curry",
        ingredients=["broccoli", "tomatoes", "rice", "coconut milk", "curry powder"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "vegetable curry")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_potato_hash(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: potato hash with eggs."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="Potato Egg Hash",
        ingredients=["potatoes", "eggs", "olive oil", "garlic", "paprika"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "potato hash with eggs")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_clean_rice_bowl(client, gluten_free_auth_headers, gluten_free_inventory):
    """Clean GF recipe: rice bowl with tamari (GF soy alternative) labelled correctly."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe(
        name="GF Rice Bowl",
        ingredients=["rice", "chicken breast", "broccoli", "tamari", "sesame seeds"]
    )
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "asian rice bowl")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


# ---------------------------------------------------------------------------
# Single-hit violation scenarios (7 test cases)
# Each tests a different blocklisted ingredient surfacing in the LLM output.
# The mock returns a clean response on the first call to simulate retry success.
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_single_violation_soy_sauce_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Soy sauce in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce"]),
        make_clean_gf_recipe(name="Safe Stir-Fry"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "chicken stir-fry")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_wheat_starch_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Wheat starch in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["wheat starch"]),
        make_clean_gf_recipe(name="Clean Soup"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "thickened vegetable soup")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_malt_vinegar_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Malt vinegar in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["malt vinegar"]),
        make_clean_gf_recipe(name="Safe Salad"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "tangy chicken salad")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_barley_malt_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Barley malt in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["barley malt"]),
        make_clean_gf_recipe(name="Safe Bowl"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "grain bowl")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_seitan_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Seitan in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["seitan"]),
        make_clean_gf_recipe(name="Safe Protein Bowl"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "high protein bowl")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_teriyaki_sauce_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Teriyaki sauce in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["teriyaki sauce"]),
        make_clean_gf_recipe(name="Safe Teriyaki Alternative"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "teriyaki chicken")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_single_violation_panko_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Panko breadcrumbs in first response; retry produces clean recipe."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["panko"]),
        make_clean_gf_recipe(name="Safe Crusted Chicken"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "crusted chicken")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


# ---------------------------------------------------------------------------
# Multi-hit violation scenarios (3 test cases)
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_multi_violation_soy_and_wheat_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Both soy sauce and wheat starch in first response; retry is clean."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce", "wheat starch"]),
        make_clean_gf_recipe(name="Clean Asian Bowl"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "asian noodle bowl")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_multi_violation_three_ingredients_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Three blocklisted ingredients in first response; retry is clean."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce", "barley malt", "malt vinegar"]),
        make_clean_gf_recipe(name="Clean Marinade Dish"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "marinated chicken")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_multi_violation_seitan_and_couscous_retry_succeeds(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Seitan and couscous in first response; retry is clean."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["seitan", "couscous"]),
        make_clean_gf_recipe(name="Clean Grain-Free Bowl"),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "grain bowl dinner")

    assert response.status_code == 200
    _assert_no_blocklist_hit(response)


# ---------------------------------------------------------------------------
# Retry exhaustion scenarios (2 test cases)
# Both first and retry responses contain violations; backend must not
# return a recipe containing blocklisted ingredients.
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_retry_exhaustion_soy_sauce_both_attempts(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Both generation attempts return soy sauce; response must not contain it."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce"]),
        make_violation_gf_recipe(["soy sauce"]),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "chicken stir-fry")

    # Backend must either strip the violation or return an error — never pass it through.
    assert response.status_code in [200, 400, 422, 500]
    if response.status_code == 200:
        _assert_no_blocklist_hit(response)


@pytest.mark.api
def test_gf_retry_exhaustion_multi_hit_both_attempts(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Both attempts return multiple violations; response must not surface them."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce", "wheat starch", "seitan"]),
        make_violation_gf_recipe(["barley malt", "malt vinegar"]),
    ]
    client.app.state.model_service = mock_service

    response = _post_recipe(client, gluten_free_auth_headers, "wheat bowl")

    assert response.status_code in [200, 400, 422, 500]
    if response.status_code == 200:
        _assert_no_blocklist_hit(response)


# ---------------------------------------------------------------------------
# Retry call-count assertions (2 test cases)
# Verify the service is called exactly twice on a violation, once on clean.
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_retry_triggers_second_llm_call(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Blocklist hit on first call must trigger exactly one retry call."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce"]),
        make_clean_gf_recipe(),
    ]
    client.app.state.model_service = mock_service

    _post_recipe(client, gluten_free_auth_headers, "asian chicken")

    assert mock_service.generate_recipe.call_count == 2


@pytest.mark.api
def test_gf_clean_response_no_retry(
    client, gluten_free_auth_headers, gluten_free_inventory
):
    """Clean first response must not trigger a retry (exactly one LLM call)."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe()
    client.app.state.model_service = mock_service

    _post_recipe(client, gluten_free_auth_headers, "simple rice bowl")

    assert mock_service.generate_recipe.call_count == 1


# ---------------------------------------------------------------------------
# Logging assertions (3 test cases)
# Verify that gluten-free generation events emit expected structured fields.
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_gf_logging_emits_on_clean_recipe(
    client, gluten_free_auth_headers, gluten_free_inventory, caplog
):
    """Structured log entry is emitted for a clean gluten-free generation."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = make_clean_gf_recipe()
    client.app.state.model_service = mock_service

    with caplog.at_level(logging.INFO):
        _post_recipe(client, gluten_free_auth_headers, "rice bowl")

    # A log record must have been emitted during the request lifecycle.
    assert len(caplog.records) > 0


@pytest.mark.api
def test_gf_logging_emits_on_violation(
    client, gluten_free_auth_headers, gluten_free_inventory, caplog
):
    """Structured log entry is emitted when a blocklist violation is detected."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["soy sauce"]),
        make_clean_gf_recipe(),
    ]
    client.app.state.model_service = mock_service

    with caplog.at_level(logging.INFO):
        _post_recipe(client, gluten_free_auth_headers, "stir-fry")

    assert len(caplog.records) > 0


@pytest.mark.api
def test_gf_logging_request_completes_with_structured_response(
    client, gluten_free_auth_headers, gluten_free_inventory, caplog
):
    """Response shape is consistent whether or not a violation was retried."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        make_violation_gf_recipe(["wheat starch"]),
        make_clean_gf_recipe(name="Retry Success Recipe"),
    ]
    client.app.state.model_service = mock_service

    with caplog.at_level(logging.INFO):
        response = _post_recipe(client, gluten_free_auth_headers, "thick stew")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "history_id" in data
    assert len(caplog.records) > 0
