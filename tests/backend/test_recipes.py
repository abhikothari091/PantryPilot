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
        user_query="test",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    response = client.post(f"/recipes/{history.id}/feedback",
        headers=auth_headers,
        json={"score": 2}
    )
    
    assert response.status_code == 200
    test_db.refresh(history)
    assert history.feedback_score == 2

@pytest.mark.api
def test_submit_feedback_dislike(client, auth_headers, test_db, test_user):
    """Test submitting negative feedback."""
    from models import RecipeHistory
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json={"recipe": {"name": "Test"}},
        user_query="test",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    response = client.post(f"/recipes/{history.id}/feedback",
        headers=auth_headers,
        json={"score": 1}
    )
    
    assert response.status_code == 200
    test_db.refresh(history)
    assert history.feedback_score == 1


# ---------------------------------------------------------------------------
# Dietary constraint blocklist unit tests
# ---------------------------------------------------------------------------

def test_build_negative_constraint_gluten_free():
    """Gluten-free flag produces constraint string covering soy sauce and key gluten sources."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["gluten-free"])
    assert "Do not include:" in result
    assert "soy sauce" in result
    assert "barley" in result
    assert "rye" in result
    assert "wheat flour" in result

def test_build_negative_constraint_vegan():
    """Vegan flag produces constraint string covering honey and gelatin."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["vegan"])
    assert "Do not include:" in result
    assert "honey" in result
    assert "gelatin" in result

def test_build_negative_constraint_dairy_free():
    """Dairy-free flag produces constraint string covering butter, cream, and cheese."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["dairy-free"])
    assert "Do not include:" in result
    assert "butter" in result
    assert "cream" in result
    assert "cheese" in result

def test_build_negative_constraint_nut_free():
    """Nut-free flag produces constraint string covering tree nuts and peanuts."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["nut-free"])
    assert "Do not include:" in result
    assert "peanuts" in result
    assert "almonds" in result
    assert "walnuts" in result
    assert "cashews" in result
    assert "pecans" in result

def test_build_negative_constraint_multiple_flags():
    """Multiple active flags each append their own constraint line."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["vegan", "gluten-free"])
    lines = result.split("\n")
    assert len(lines) == 2
    assert all(line.startswith("Do not include:") for line in lines)
    # vegan line covers honey; gluten-free line covers soy sauce
    assert any("honey" in line for line in lines)
    assert any("soy sauce" in line for line in lines)

def test_build_negative_constraint_no_flags():
    """Empty flag list returns empty string."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string([])
    assert result == ""

def test_build_negative_constraint_unknown_flag():
    """Unrecognized dietary flag is silently ignored."""
    from model_service import build_negative_constraint_string
    result = build_negative_constraint_string(["keto"])
    assert result == ""
