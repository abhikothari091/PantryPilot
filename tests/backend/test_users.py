"""
Tests for user profile endpoints.
"""

import pytest

@pytest.mark.api
def test_get_profile(client, auth_headers, test_user):
    """Test retrieving user profile."""
    response = client.get("/users/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "vegan" in data["dietary_restrictions"]
    assert "peanuts" in data["allergies"]
    assert "Italian" in data["favorite_cuisines"]

@pytest.mark.api
def test_get_profile_without_auth(client):
    """Test profile endpoint requires authentication."""
    response = client.get("/users/profile")
    assert response.status_code == 401

@pytest.mark.api
def test_update_profile_dietary_restrictions(client, auth_headers, test_db, test_user):
    """Test updating dietary restrictions."""
    response = client.put("/users/profile",
        headers=auth_headers,
        json={
            "dietary_restrictions": ["vegetarian", "gluten-free"],
            "allergies": ["peanuts"],
            "favorite_cuisines": ["Italian"]
        }
    )
    
    assert response.status_code == 200
    
    # Verify update
    from models import UserProfile
    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    assert "vegetarian" in profile.dietary_restrictions
    assert "gluten-free" in profile.dietary_restrictions
    assert "vegan" not in profile.dietary_restrictions

@pytest.mark.api
def test_update_profile_allergies(client, auth_headers, test_db, test_user):
    """Test updating allergies."""
    response = client.put("/users/profile",
        headers=auth_headers,
        json={
            "dietary_restrictions": ["vegan"],
            "allergies": ["shellfish", "dairy"],
            "favorite_cuisines": ["Japanese"]
        }
    )
    
    assert response.status_code == 200
    
    from models import UserProfile
    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    assert "shellfish" in profile.allergies
    assert "dairy" in profile.allergies

@pytest.mark.api
def test_update_profile_cuisines(client, auth_headers, test_db, test_user):
    """Test updating favorite cuisines."""
    response = client.put("/users/profile",
        headers=auth_headers,
        json={
            "dietary_restrictions": [],
            "allergies": [],
            "favorite_cuisines": ["Mexican", "Indian", "Thai"]
        }
    )
    
    assert response.status_code == 200
    
    from models import UserProfile
    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    assert len(profile.favorite_cuisines) == 3
    assert "Mexican" in profile.favorite_cuisines

@pytest.mark.api
def test_update_profile_empty_lists(client, auth_headers, test_db, test_user):
    """Test updating profile with empty lists."""
    response = client.put("/users/profile",
        headers=auth_headers,
        json={
            "dietary_restrictions": [],
            "allergies": [],
            "favorite_cuisines": []
        }
    )
    
    assert response.status_code == 200
    
    from models import UserProfile
    profile = test_db.query(UserProfile).filter_by(user_id=test_user.id).first()
    assert profile.dietary_restrictions == []
    assert profile.allergies == []
    assert profile.favorite_cuisines == []
