import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models import User, UserProfile
from auth_utils import get_password_hash, create_access_token

def test_admin_metrics_access_denied_for_non_admin(client: TestClient, test_db: Session):
    # Create a unique non-admin user for this test
    non_admin_user = User(
        username="nonadmin_user",
        email="nonadmin@example.com",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(non_admin_user)
    test_db.commit()
    test_db.refresh(non_admin_user)
    
    # Generate token
    token = create_access_token(data={"sub": non_admin_user.username})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/admin/metrics", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_admin_metrics_access_success_for_admin(client: TestClient, test_db: Session):
    # Create admin user
    admin_data = {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": get_password_hash("Abhi@AK47")
    }
    admin = User(**admin_data)
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    
    # Login to get token
    response = client.post("/auth/token", data={"username": "admin", "password": "Abhi@AK47"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Access metrics
    response = client.get("/admin/metrics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "recipes" in data
    assert "inventory" in data
    assert "dpo" in data

def test_seed_admin_user(client: TestClient, test_db: Session):
    # Ensure admin doesn't exist
    test_db.query(User).filter(User.username == "admin").delete()
    test_db.commit()
    
    response = client.post("/admin/seed")
    assert response.status_code == 200
    assert response.json()["created"] is True
    
    # Check if created
    admin = test_db.query(User).filter(User.username == "admin").first()
    assert admin is not None
    assert admin.email == "kothari.abhi@northeastern.edu"

def test_seed_admin_user_already_exists(client: TestClient, test_db: Session):
    # Seed once
    client.post("/admin/seed")
    
    # Seed again
    response = client.post("/admin/seed")
    assert response.status_code == 200
    assert response.json()["created"] is False
