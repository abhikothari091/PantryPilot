"""
Tests for recipe endpoints (generation, cooked, feedback, warmup).
"""

import pytest
import json
from unittest.mock import patch, Mock

@pytest.mark.api
def test_generate_recipe_success(client, auth_headers, test_inventory_items):
    """Test successful recipe generation."""
    # Mock the model_service in app.state
    mock_service = Mock()
    mock_service.generate_recipe.return_value = '''{
        "status": "ok",
        "missing_ingredients": ["salt"],
        "recipe": {
            "name": "Test Recipe",
            "cuisine": "Italian",
            "culinary_preference": "none",
            "time": "30 mins",
            "main_ingredients": ["pasta", "tomato"],
            "steps": "Step 1. Boil water. Step 2. Cook pasta.",
            "note": null
        },
        "shopping_list": ["salt"]
    }'''
    
    # Inject mock into client's app
    client.app.state.model_service = mock_service
    
    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={
            "user_request": "Quick pasta dinner",
            "servings": 2
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "history_id" in data

@pytest.mark.api
def test_generate_recipe_saves_history(client, auth_headers, test_db, test_user):
    """Test recipe generation saves to history."""
    mock_service = Mock()
    mock_service.generate_recipe.return_value = '''{
        "status": "ok",
        "missing_ingredients": [],
        "recipe": {
            "name": "Italian Dinner",
            "cuisine": "Italian",
            "culinary_preference": "none",
            "time": "45 mins",
            "main_ingredients": ["pasta", "sauce"],
            "steps": "Step 1. Cook. Step 2. Serve.",
            "note": null
        },
        "shopping_list": []
    }'''
    client.app.state.model_service = mock_service
    
    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={
            "user_request": "Italian dinner",
            "servings": 4
        }
    )
    
    history_id = response.json()["history_id"]
    
    # Verify history entry exists
    from models import RecipeHistory
    history = test_db.query(RecipeHistory).filter_by(id=history_id).first()
    assert history is not None
    assert history.user_id == test_user.id
    assert history.servings == 4
    assert "italian" in history.user_query.lower()

@pytest.mark.api
def test_mark_recipe_cooked(client, auth_headers, test_db, test_user, test_inventory_items):
    """Test marking recipe as cooked deducts inventory."""
    from models import RecipeHistory
    
    # Create a recipe history entry
    recipe_json = {
        "recipe": {
            "name": "Chicken Rice",
            "main_ingredients": ["2 lb chicken breast", "1 kg rice"]
        }
    }
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json=recipe_json,
        user_query="Chicken dinner",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    # Get initial quantities
    from models import InventoryItem
    chicken = test_db.query(InventoryItem).filter_by(
        user_id=test_user.id, 
        item_name="Chicken Breast"
    ).first()
    rice = test_db.query(InventoryItem).filter_by(
        user_id=test_user.id,
        item_name="Rice"
    ).first()
    
    initial_chicken = chicken.quantity
    initial_rice = rice.quantity
    
    # Mark as cooked
    response = client.post(f"/recipes/{history.id}/cooked", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Refresh from DB
    test_db.refresh(chicken)
    test_db.refresh(rice)
    test_db.refresh(history)
    
    # Verify quantities decreased
    assert chicken.quantity < initial_chicken
    assert rice.quantity < initial_rice
    assert history.is_cooked is True

@pytest.mark.api
def test_mark_nonexistent_recipe_cooked(client, auth_headers):
    """Test marking non-existent recipe as cooked returns 404."""
    response = client.post("/recipes/99999/cooked", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.api
def test_submit_feedback_like(client, auth_headers, test_db, test_user):
    """Test submitting positive feedback."""
    from models import RecipeHistory
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json={"recipe": {"name": "Test"}},
        user_query="Test query",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    response = client.post(f"/recipes/{history.id}/feedback",
        headers=auth_headers,
        json={"score": 2}  # Like
    )
    
    assert response.status_code == 200
    
    # Verify feedback saved
    test_db.refresh(history)
    assert history.feedback_score == 2

@pytest.mark.api
def test_submit_feedback_dislike(client, auth_headers, test_db, test_user):
    """Test submitting negative feedback."""
    from models import RecipeHistory
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json={"recipe": {"name": "Test"}},
        user_query="Test query",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    response = client.post(f"/recipes/{history.id}/feedback",
        headers=auth_headers,
        json={"score": 1}  # Dislike
    )
    
    assert response.status_code == 200
    test_db.refresh(history)
    assert history.feedback_score == 1

@pytest.mark.api
def test_generate_recipe_comparison_on_seventh_request(client, auth_headers, test_db, test_user):
    """Every 7th generation should return two variants for preference collection."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        json.dumps({"recipe": {"name": "Variant A", "main_ingredients": []}}),
        json.dumps({"recipe": {"name": "Variant B", "main_ingredients": []}})
    ]
    client.app.state.model_service = mock_service

    from models import UserProfile, RecipePreference, RecipeHistory

    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    profile.recipe_generation_count = 6  # Pretend the user has already generated 6 recipes
    test_db.commit()

    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={
            "user_request": "DPO comparison request",
            "servings": 2
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "comparison"
    assert "variant_a" in data["data"]
    assert "variant_b" in data["data"]
    assert mock_service.generate_recipe.call_count == 2

    # Generation count incremented to 7
    test_db.refresh(profile)
    assert profile.recipe_generation_count == 7

    # Preference record stored and no history written yet
    preference = test_db.query(RecipePreference).filter_by(user_id=test_user.id).first()
    assert preference is not None
    assert preference.prompt == "DPO comparison request"
    assert test_db.query(RecipeHistory).count() == 0

@pytest.mark.api
def test_choose_preference_adds_history(client, auth_headers, test_db, test_user):
    """Choosing a variant should write to history and mark preference."""
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = [
        json.dumps({"recipe": {"name": "Variant A"}}),
        json.dumps({"recipe": {"name": "Variant B"}}),
    ]
    client.app.state.model_service = mock_service

    from models import UserProfile, RecipePreference, RecipeHistory

    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    profile.recipe_generation_count = 6
    test_db.commit()

    # Trigger comparison
    compare_res = client.post("/recipes/generate",
        headers=auth_headers,
        json={"user_request": "choose test", "servings": 2}
    )
    pref_id = compare_res.json()["preference_id"]

    # Choose variant A
    choose_res = client.post(f"/recipes/preference/{pref_id}/choose",
        headers=auth_headers,
        json={"chosen_variant": "A", "servings": 2}
    )
    assert choose_res.status_code == 200
    data = choose_res.json()
    assert data["history_id"] is not None

    test_db.refresh(profile)
    pref = test_db.query(RecipePreference).filter_by(id=pref_id).first()
    assert pref.chosen_variant == "A"
    assert pref.rejected_variant == "B"
    assert pref.chosen_recipe_history_id == data["history_id"]

    # History written
    history = test_db.query(RecipeHistory).filter_by(id=data["history_id"]).first()
    assert history is not None
    assert history.recipe_json["recipe"]["name"] == "Variant A"

@pytest.mark.api
def test_get_recipe_history(client, auth_headers, test_db, test_user):
    """Test retrieving recipe history."""
    from models import RecipeHistory
    from datetime import datetime, timedelta
    
    # Create multiple history entries
    recipes = [
        RecipeHistory(
            user_id=test_user.id,
            recipe_json={"recipe": {"name": f"Recipe {i}"}},
            user_query=f"Query {i}",
            servings=2,
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        for i in range(3)
    ]
    
    for recipe in recipes:
        test_db.add(recipe)
    test_db.commit()
    
    response = client.get("/recipes/history", headers=auth_headers)
    

@pytest.mark.api
def test_gluten_free_profile_injects_blocklist(client, auth_headers, test_db, test_user):
    """Blocklist constraint is injected into generate_recipe call when profile is gluten-free."""
    from models import UserProfile
    from model_service import HIDDEN_GLUTEN_BLOCKLIST

    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    profile.dietary_restrictions = ["gluten-free"]
    test_db.commit()

    mock_service = Mock()
    mock_service.generate_recipe.return_value = json.dumps({"recipe": {"name": "GF Bowl", "main_ingredients": []}})
    client.app.state.model_service = mock_service

    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={"user_request": "gluten free lunch", "servings": 2}
    )

    assert response.status_code == 200
    mock_service.generate_recipe.assert_called_once()
    call_preferences = mock_service.generate_recipe.call_args[0][1]
    dietary = call_preferences.get("dietary_restrictions", [])
    assert any("gluten" in d.lower() for d in dietary)


@pytest.mark.api
def test_gluten_free_blocklist_content_in_prompt():
    """generate_recipe builds a prompt containing all blocklist items for gluten-free profiles."""
    from model_service import ModelService, HIDDEN_GLUTEN_BLOCKLIST
    from unittest.mock import patch, Mock

    service = ModelService.__new__(ModelService)
    service.api_url = "http://fake"
    service.timeout = 5

    captured_payload = {}

    def fake_post(url, json, timeout):
        captured_payload.update(json)
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"recipe": {"status": "ok", "recipe": {}}}
        return mock_resp

    with patch("model_service.requests.post", side_effect=fake_post):
        service.generate_recipe(
            inventory=[],
            preferences={"dietary_restrictions": ["gluten-free"], "allergies": [], "favorite_cuisines": []},
            user_request="test"
        )

    prompt_text = captured_payload.get("user_request", "") + captured_payload.get("preferences", {}).get("custom_preferences", "")
    for item in HIDDEN_GLUTEN_BLOCKLIST:
        assert item in prompt_text, f"Expected blocklist item '{item}' in prompt"

    assert len(HIDDEN_GLUTEN_BLOCKLIST) >= 10


@pytest.mark.api
def test_non_gluten_free_profile_no_blocklist():
    """generate_recipe does NOT include hidden-gluten blocklist for non-gluten-free profiles."""
    from model_service import ModelService, HIDDEN_GLUTEN_BLOCKLIST
    from unittest.mock import patch, Mock

    service = ModelService.__new__(ModelService)
    service.api_url = "http://fake"
    service.timeout = 5

    captured_payload = {}

    def fake_post(url, json, timeout):
        captured_payload.update(json)
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"recipe": {"status": "ok", "recipe": {}}}
        return mock_resp

    with patch("model_service.requests.post", side_effect=fake_post):
        service.generate_recipe(
            inventory=[],
            preferences={"dietary_restrictions": ["vegan"], "allergies": [], "favorite_cuisines": []},
            user_request="test"
        )

    prompt_text = captured_payload.get("user_request", "") + captured_payload.get("preferences", {}).get("custom_preferences", "")
    # None of the hidden-gluten specific blocklist phrase should appear
    assert "HIDDEN GLUTEN SOURCES" not in prompt_text
    # Spot-check a few individual items are also absent
    assert "soy sauce" not in prompt_text
    assert "seitan" not in prompt_text
