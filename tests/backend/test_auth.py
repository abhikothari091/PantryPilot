"""
Tests for authentication endpoints (register, login, JWT).
"""

import pytest
from jose import jwt
from auth_utils import SECRET_KEY, ALGORITHM

@pytest.mark.auth
def test_register_new_user(client):
    """Test user registration with valid data."""
    response = client.post("/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "securepass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify token is valid
    token = data["access_token"]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "newuser"

@pytest.mark.auth
def test_register_duplicate_username(client, test_user):
    """Test registration fails with duplicate username."""
    response = client.post("/auth/register", json={
        "username": test_user.username,
        "email": "different@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

@pytest.mark.auth
def test_login_success(client, test_user):
    """Test successful login with correct credentials."""
    response = client.post("/auth/token", data={
        "username": "testuser",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.auth
def test_login_wrong_password(client, test_user):
    """Test login fails with incorrect password."""
    response = client.post("/auth/token", data={
        "username": "testuser",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()

@pytest.mark.auth
def test_login_nonexistent_user(client):
    """Test login fails for non-existent user."""
    response = client.post("/auth/token", data={
        "username": "nosuchuser",
        "password": "anypassword"
    })
    
    assert response.status_code == 401

@pytest.mark.auth
def test_access_protected_endpoint_without_token(client):
    """Test protected endpoint rejects request without token."""
    response = client.get("/inventory/")
    assert response.status_code == 401

@pytest.mark.auth
def test_access_protected_endpoint_with_token(client, auth_headers):
    """Test protected endpoint accepts valid token."""
    response = client.get("/inventory/", headers=auth_headers)
    assert response.status_code == 200

@pytest.mark.auth
def test_invalid_token_format(client):
    """Test endpoint rejects malformed token."""
    response = client.get("/inventory/", headers={
        "Authorization": "Bearer invalid_token_format"
    })
    assert response.status_code == 401

@pytest.mark.auth
def test_expired_token_handling(client):
    """Test endpoint rejects expired token."""
    # Create token with negative expiry
    from datetime import timedelta
    from auth_utils import create_access_token
    
    expired_token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(minutes=-10)
    )
    
    response = client.get("/inventory/", headers={
        "Authorization": f"Bearer {expired_token}"
    })
    assert response.status_code == 401
