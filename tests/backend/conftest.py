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


# ---------------------------------------------------------------------------
# Gluten-free test fixtures
# ---------------------------------------------------------------------------

# Canonical blocklist — mirrors what Task 1 injected into the system prompt.
# Update this list if the backend blocklist module changes.
GLUTEN_BLOCKLIST = [
    "soy sauce",
    "wheat starch",
    "malt vinegar",
    "barley malt",
    "regular oats",
    "seitan",
    "teriyaki sauce",
    "wheat flour",
    "bread crumbs",
    "panko",
    "bulgur",
    "farro",
    "spelt",
    "kamut",
    "triticale",
    "semolina",
    "durum",
    "couscous",
    "wheat germ",
    "wheat bran",
]


@pytest.fixture
def gluten_free_user(test_db):
    """Test user whose profile declares gluten-free dietary restriction."""
    from auth_utils import get_password_hash

    user = User(
        username="gfuser",
        email="gfuser@example.com",
        hashed_password=get_password_hash("gfpass123")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        dietary_restrictions=["gluten-free"],
        allergies=[],
        favorite_cuisines=["Asian", "Mediterranean"]
    )
    test_db.add(profile)
    test_db.commit()

    return user


@pytest.fixture
def gluten_free_auth_headers(gluten_free_user):
    """Bearer token headers for the gluten-free test user."""
    token = create_access_token(data={"sub": gluten_free_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def gluten_free_inventory(test_db, gluten_free_user):
    """Inventory stocked with naturally gluten-free ingredients."""
    items = [
        InventoryItem(user_id=gluten_free_user.id, item_name="Rice", quantity=2.0, unit="kg", category="pantry"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Chicken Breast", quantity=1.0, unit="lb", category="meat"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Broccoli", quantity=0.5, unit="kg", category="produce"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Olive Oil", quantity=0.3, unit="L", category="pantry"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Garlic", quantity=0.1, unit="kg", category="produce"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Tomatoes", quantity=0.5, unit="kg", category="produce"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Eggs", quantity=6.0, unit="pcs", category="dairy"),
        InventoryItem(user_id=gluten_free_user.id, item_name="Potatoes", quantity=1.0, unit="kg", category="produce"),
    ]
    for item in items:
        test_db.add(item)
    test_db.commit()
    return items


def make_clean_gf_recipe(name="Safe GF Recipe", ingredients=None):
    """Build a recipe JSON string containing no blocklisted ingredients."""
    if ingredients is None:
        ingredients = ["rice", "chicken breast", "broccoli", "olive oil", "garlic"]
    return f'{{
        "status": "ok",
        "missing_ingredients": [],
        "recipe": {{
            "name": "{name}",
            "cuisine": "Asian",
            "culinary_preference": "gluten-free",
            "time": "30 mins",
            "main_ingredients": {str(ingredients).replace("'", '"')},
            "steps": "Step 1. Cook rice. Step 2. Stir-fry chicken with garlic and broccoli. Step 3. Serve.",
            "note": "All ingredients are gluten-free."
        }},
        "shopping_list": []
    }}'


def make_violation_gf_recipe(violating_ingredients):
    """Build a recipe JSON string that contains one or more blocklisted ingredients."""
    all_ingredients = ["rice", "chicken breast"] + violating_ingredients
    ingredients_json = str(all_ingredients).replace("'", '"')
    steps = "Step 1. Cook rice. Step 2. Add " + ", ".join(violating_ingredients) + ". Step 3. Serve."
    return f'{{
        "status": "ok",
        "missing_ingredients": [],
        "recipe": {{
            "name": "Unsafe Recipe",
            "cuisine": "Asian",
            "culinary_preference": "none",
            "time": "25 mins",
            "main_ingredients": {ingredients_json},
            "steps": "{steps}",
            "note": null
        }},
        "shopping_list": []
    }}'
