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
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Should be sorted newest first
    assert "Recipe 0" in str(data[0]["recipe_json"])

@pytest.mark.api
def test_warmup_endpoint(client, auth_headers):
    """Test warmup endpoint returns immediately."""
    mock_service = Mock()
    client.app.state.model_service = mock_service
    
    response = client.post("/recipes/warmup", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "warming"
    assert "message" in data

@pytest.mark.api
def test_warmup_does_not_block(client, auth_headers):
    """Test warmup endpoint is non-blocking."""
    import time
    
    # Mock slow LLM service
    def slow_generate(*args, **kwargs):
        time.sleep(2)  # Simulate slow call
        return "{}"
    
    mock_service = Mock()
    mock_service.generate_recipe.side_effect = slow_generate
    client.app.state.model_service = mock_service
    
    start = time.time()
    response = client.post("/recipes/warmup", headers=auth_headers)
    elapsed = time.time() - start
    
    # Should return in < 0.5s even though LLM takes 2s
    assert elapsed < 0.5
    assert response.status_code == 200

@pytest.mark.api
def test_recipe_history_user_isolation(client, test_db):
    """Test users can only see their own recipe history."""
    from auth_utils import get_password_hash, create_access_token
    from models import User, RecipeHistory
    
    # Create two users
    user1 = User(username="user1", email="u1@test.com", 
                 hashed_password=get_password_hash("pass"))
    user2 = User(username="user2", email="u2@test.com",
                 hashed_password=get_password_hash("pass"))
    test_db.add_all([user1, user2])
    test_db.commit()
    test_db.refresh(user1)
    test_db.refresh(user2)
    
    # Create recipes for each
    recipe1 = RecipeHistory(user_id=user1.id, recipe_json={}, 
                           user_query="User1 recipe", servings=2)
    recipe2 = RecipeHistory(user_id=user2.id, recipe_json={},
                           user_query="User2 recipe", servings=2)
    test_db.add_all([recipe1, recipe2])
    test_db.commit()
    
    # User1 should only see their recipe
    token1 = create_access_token(data={"sub": "user1"})
    response = client.get("/recipes/history", 
                         headers={"Authorization": f"Bearer {token1}"})
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_query"] == "User1 recipe"
