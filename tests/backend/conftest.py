"""
Pytest configuration and fixtures for backend tests.
Provides test database, FastAPI client, and common mocks.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "model_deployment" / "backend"
sys.path.insert(0, str(backend_path))

from main import app
from database import get_db
from models import Base, User, UserProfile, InventoryItem, RecipeHistory
from auth_utils import create_access_token

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with overridden database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_model_service():
    """Mock external LLM service."""
    with patch('model_service.ModelService') as mock:
        mock_instance = Mock()
        mock_instance.generate_recipe.return_value = '''{
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
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def test_user(test_db):
    """Create a test user in the database."""
    from auth_utils import get_password_hash
    
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    # Create profile
    profile = UserProfile(
        user_id=user.id,
        dietary_restrictions=["vegan"],
        allergies=["peanuts"],
        favorite_cuisines=["Italian", "Chinese"]
    )
    test_db.add(profile)
    test_db.commit()
    
    return user

@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user."""
    return create_access_token(data={"sub": test_user.username})

@pytest.fixture
def auth_headers(auth_token):
    """Headers with Bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def test_inventory_items(test_db, test_user):
    """Create test inventory items."""
    items = [
        InventoryItem(
            user_id=test_user.id,
            item_name="Chicken Breast",
            quantity=2.0,
            unit="lb",
            category="meat"
        ),
        InventoryItem(
            user_id=test_user.id,
            item_name="Rice",
            quantity=1.5,
            unit="kg",
            category="pantry"
        ),
        InventoryItem(
            user_id=test_user.id,
            item_name="Tomatoes",
            quantity=0.05,  # Low stock
            unit="kg",
            category="produce"
        ),
    ]
    
    for item in items:
        test_db.add(item)
    test_db.commit()
    
    return items

@pytest.fixture
def mock_ocr_response():
    """Mock OCR API response."""
    return {
        "status": "success",
        "detected_items": [
            {"item_name": "Milk", "quantity": 1, "unit": "L"},
            {"item_name": "Bread", "quantity": 2, "unit": "pcs"},
            {"item_name": "Eggs", "quantity": 12, "unit": "pcs"},
        ]
    }

@pytest.fixture
def mock_requests(mock_ocr_response):
    """Mock external HTTP requests."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ocr_response
        mock_post.return_value = mock_response
        yield mock_post
