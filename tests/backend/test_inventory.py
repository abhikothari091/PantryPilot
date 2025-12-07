"""
Tests for inventory endpoints (CRUD operations, OCR upload).
"""

import pytest
from io import BytesIO

@pytest.mark.api
def test_get_inventory_empty(client, auth_headers):
    """Test getting inventory when user has no items."""
    response = client.get("/inventory/", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.api
def test_get_inventory_with_items(client, auth_headers, test_inventory_items):
    """Test getting inventory returns user's items."""
    response = client.get("/inventory/", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert any(item["item_name"] == "Chicken Breast" for item in data)
    assert any(item["item_name"] == "Rice" for item in data)

@pytest.mark.api
def test_add_inventory_item(client, auth_headers):
    """Test adding new inventory item."""
    response = client.post("/inventory/", 
        headers=auth_headers,
        json={
            "item_name": "Olive Oil",
            "quantity": 0.5,
            "unit": "L",
            "category": "pantry"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "item_id" in data
    
    # Verify item was added
    get_response = client.get("/inventory/", headers=auth_headers)
    items = get_response.json()
    assert any(item["item_name"] == "Olive Oil" for item in items)

@pytest.mark.api
def test_update_inventory_item(client, auth_headers, test_inventory_items):
    """Test updating existing inventory item."""
    item_id = test_inventory_items[0].id
    
    response = client.put(f"/inventory/{item_id}",
        headers=auth_headers,
        json={
            "item_name": "Chicken Breast",
            "quantity": 3.0,  # Updated quantity
            "unit": "lb",
            "category": "meat"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["item"]["quantity"] == 3.0

@pytest.mark.api
def test_update_nonexistent_item(client, auth_headers):
    """Test updating non-existent item returns 404."""
    response = client.put("/inventory/99999",
        headers=auth_headers,
        json={
            "item_name": "Test",
            "quantity": 1.0,
            "unit": "kg",
            "category": "pantry"
        }
    )
    
    assert response.status_code == 404

@pytest.mark.api
def test_delete_inventory_item(client, auth_headers, test_inventory_items):
    """Test deleting inventory item."""
    item_id = test_inventory_items[0].id
    
    response = client.delete(f"/inventory/{item_id}", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify item was deleted
    get_response = client.get("/inventory/", headers=auth_headers)
    items = get_response.json()
    assert len(items) == 2  # Originally had 3
    assert not any(item["id"] == item_id for item in items)

@pytest.mark.api
def test_delete_nonexistent_item(client, auth_headers):
    """Test deleting non-existent item returns 404."""
    response = client.delete("/inventory/99999", headers=auth_headers)
    assert response.status_code == 404

@pytest.mark.integration
def test_ocr_upload_success(client, auth_headers, mock_requests):
    """Test OCR receipt upload with successful detection."""
    # Create fake image file
    fake_image = BytesIO(b"fake image data")
    fake_image.name = "receipt.jpg"
    
    response = client.post("/inventory/upload",
        headers=auth_headers,
        files={"file": ("receipt.jpg", fake_image, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "detected_items" in data
    assert len(data["detected_items"]) > 0

@pytest.mark.integration
def test_confirm_upload(client, auth_headers):
    """Test bulk confirmation of OCR detected items."""
    items_to_add = [
        {"item_name": "Milk", "quantity": 1, "unit": "L", "category": "dairy"},
        {"item_name": "Bread", "quantity": 2, "unit": "pcs", "category": "pantry"},
    ]
    
    response = client.post("/inventory/confirm_upload",
        headers=auth_headers,
        json=items_to_add
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 2
    
    # Verify items were added
    get_response = client.get("/inventory/", headers=auth_headers)
    items = get_response.json()
    assert any(item["item_name"] == "Milk" for item in items)
    assert any(item["item_name"] == "Bread" for item in items)

@pytest.mark.api
def test_inventory_isolation_between_users(client, test_db):
    """Test that users can only see their own inventory."""
    from auth_utils import get_password_hash, create_access_token
    from models import User, InventoryItem
    
    # Create second user
    user2 = User(
        username="user2",
        email="user2@example.com",
        hashed_password=get_password_hash("pass123")
    )
    test_db.add(user2)
    test_db.commit()
    test_db.refresh(user2)
    
    # Add item for user2
    item = InventoryItem(
        user_id=user2.id,
        item_name="User2 Item",
        quantity=1.0,
        unit="pcs",
        category="pantry"
    )
    test_db.add(item)
    test_db.commit()
    
    # Try to access with user2's token
    token2 = create_access_token(data={"sub": "user2"})
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    response = client.get("/inventory/", headers=headers2)
    items = response.json()
    
    # Should only see user2's item
    assert len(items) == 1
    assert items[0]["item_name"] == "User2 Item"
