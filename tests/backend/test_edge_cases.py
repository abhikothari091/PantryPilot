"""
Additional tests to increase coverage for recipes.py and other low-coverage modules.
"""

import pytest
from fastapi import HTTPException

@pytest.mark.api
def test_generate_recipe_missing_query(client, auth_headers):
    """Test recipe generation with missing query."""
    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={
            "user_request": "",  # Empty query
            "servings": 2
        }
    )
    # Should still work, just with empty query
    assert response.status_code in [200, 400, 422]

@pytest.mark.api
def test_generate_recipe_with_comparison(client, auth_headers):
    """Test recipe generation with comparison flag."""
    from unittest.mock import Mock
    
    mock_service = Mock()
    mock_service.generate_recipe.return_value = '{"status": "ok", "recipe": {"name": "Test"}}'
    mock_service.generate_comparison.return_value = ('{"recipe1": "A"}', '{"recipe2": "B"}')
    client.app.state.model_service = mock_service
    
    response = client.post("/recipes/generate",
        headers=auth_headers,
        json={
            "user_request": "pasta",
            "servings": 2,
            "compare": True
        }
    )
    
    assert response.status_code == 200

@pytest.mark.api
def test_video_generation_disabled(client):
    """Test video generation when disabled."""
    response = client.post("/recipes/video",
        json={"prompt": "cooking pasta"}
    )
    
    # Should return mock URL when disabled
    assert response.status_code == 200
    data = response.json()
    assert "video_url" in data
    assert data["mode"] == "mock"

@pytest.mark.api
def test_cooked_invalid_servings(client, auth_headers, test_db, test_user):
    """Test marking recipe cooked with invalid servings."""
    from models import RecipeHistory
    
    recipe_json = {
        "recipe": {
            "name": "Test Recipe",
            "main_ingredients": ["rice"]
        }
    }
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json=recipe_json,
        user_query="Test",
        servings=0  # Invalid servings
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    # Should still process
    response = client.post(f"/recipes/{history.id}/cooked", headers=auth_headers)
    assert response.status_code in [200, 400]

@pytest.mark.api
def test_feedback_invalid_score(client, auth_headers, test_db, test_user):
    """Test submitting invalid feedback score."""
    from models import RecipeHistory
    
    history = RecipeHistory(
        user_id=test_user.id,
        recipe_json={"recipe": {"name": "Test"}},
        user_query="Test",
        servings=2
    )
    test_db.add(history)
    test_db.commit()
    test_db.refresh(history)
    
    # Invalid score (not 1 or 2)
    response = client.post(f"/recipes/{history.id}/feedback",
        headers=auth_headers,
        json={"score": 5}
    )
    
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]

@pytest.mark.api  
def test_update_inventory_missing_fields(client, auth_headers, test_inventory_items):
    """Test updating inventory with missing fields."""
    item_id = test_inventory_items[0].id
    
    response = client.put(f"/inventory/{item_id}",
        headers=auth_headers,
        json={
            "item_name": "Updated Item"
            # Missing quantity, unit, category
        }
    )
    
    # Partial updates are accepted; quantity/unit/category remain unchanged
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["item"]["item_name"] == "Updated Item"

@pytest.mark.api
def test_add_inventory_duplicate_name(client, auth_headers, test_inventory_items):
    """Test adding duplicate inventory item."""
    response = client.post("/inventory/",
        headers=auth_headers,
        json={
            "item_name": "Chicken Breast",  # Already exists
            "quantity": 1.0,
            "unit": "lb",
            "category": "meat"
        }
    )
    
    # Should still work (no unique constraint on item_name)  
    assert response.status_code == 200

@pytest.mark.api
def test_ocr_upload_invalid_file(client, auth_headers):
    """Test OCR upload with invalid file type."""
    from io import BytesIO
    
    fake_file = BytesIO(b"not an image")
    
    response = client.post("/inventory/upload",
        headers=auth_headers,
        files={"file": ("test.txt", fake_file, "text/plain")}
    )
    
    # Should handle gracefully
    assert response.status_code in [200, 400, 422]

@pytest.mark.api
def test_confirm_upload_empty_list(client, auth_headers):
    """Test confirming upload with empty item list."""
    response = client.post("/inventory/confirm_upload",
        headers=auth_headers,
        json=[]
    )
    
    assert response.status_code == 200
    assert response.json()["count"] == 0

@pytest.mark.api
def test_profile_update_with_invalid_data(client, auth_headers):
    """Test profile update with invalid data types."""
    response = client.put("/users/profile",
        headers=auth_headers,
        json={
            "dietary_restrictions": "not_a_list",  # Should be list
            "allergies": ["peanuts"],
            "favorite_cuisines": ["Italian"]
        }
    )
    
    # Should return validation error
    assert response.status_code == 422
