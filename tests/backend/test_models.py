"""
Tests for SQLAlchemy database models.
"""

import pytest
from datetime import datetime

@pytest.mark.unit
def test_create_user(test_db):
    """Test creating a user model."""
    from models import User
    from auth_utils import get_password_hash
    
    user = User(
        username="modeltest",
        email="model@test.com",
        hashed_password=get_password_hash("password")
    )
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    assert user.id is not None
    assert user.username == "modeltest"
    assert user.created_at is not None

@pytest.mark.unit
def test_user_profile_relationship(test_db):
    """Test User-UserProfile relationship."""
    from models import User, UserProfile
    from auth_utils import get_password_hash
    
    user = User(
        username="reltest",
        email="rel@test.com",
        hashed_password=get_password_hash("pass")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    profile = UserProfile(
        user_id=user.id,
        dietary_restrictions=["vegan"],
        allergies=[],
        favorite_cuisines=["Italian"]
    )
    test_db.add(profile)
    test_db.commit()
    
    # Access via relationship
    assert user.profile is not None
    assert user.profile.dietary_restrictions == ["vegan"]
    assert profile.user.username == "reltest"

@pytest.mark.unit
def test_inventory_item_model(test_db, test_user):
    """Test creating inventory item."""
    from models import InventoryItem
    
    item = InventoryItem(
        user_id=test_user.id,
        item_name="Test Item",
        quantity=5.0,
        unit="kg",
        category="pantry"
    )
    
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)
    
    assert item.id is not None
    assert item.quantity == 5.0
    assert item.created_at is not None

@pytest.mark.unit
def test_recipe_history_model(test_db, test_user):
    """Test creating recipe history entry."""
    from models import RecipeHistory
    
    recipe = RecipeHistory(
        user_id=test_user.id,
        recipe_json={"recipe": {"name": "Test Recipe"}},
        user_query="Test query",
        servings=2,
        feedback_score=0,
        is_cooked=False
    )
    
    test_db.add(recipe)
    test_db.commit()
    test_db.refresh(recipe)
    
    assert recipe.id is not None
    assert recipe.servings == 2
    assert recipe.is_cooked is False
    assert recipe.feedback_score == 0

@pytest.mark.unit
def test_user_cascade_delete(test_db):
    """Test deleting user cascades to related records."""
    from models import User, UserProfile, InventoryItem, RecipeHistory
    from auth_utils import get_password_hash
    
    # Create user with related data
    user = User(
        username="cascade",
        email="cascade@test.com",
        hashed_password=get_password_hash("pass")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    profile = UserProfile(user_id=user.id)
    item = InventoryItem(user_id=user.id, item_name="Item", quantity=1, unit="pcs", category="pantry")
    recipe = RecipeHistory(user_id=user.id, recipe_json={}, user_query="Query", servings=2)
    
    test_db.add_all([profile, item, recipe])
    test_db.commit()
    
    # Delete user
    test_db.delete(user)
    test_db.commit()
    
    # Verify related records are deleted
    assert test_db.query(UserProfile).filter_by(user_id=user.id).first() is None
    assert test_db.query(InventoryItem).filter_by(user_id=user.id).first() is None
    assert test_db.query(RecipeHistory).filter_by(user_id=user.id).first() is None

@pytest.mark.unit
def test_json_field_serialization(test_db, test_user):
    """Test JSON field serialization/deserialization."""
    from models import UserProfile
    
    complex_data = {
        "dietary_restrictions": ["vegan", "gluten-free"],
        "allergies": ["peanuts", "shellfish"],
        "favorite_cuisines": ["Italian", "Japanese", "Mexican"]
    }
    
    profile = UserProfile(
        user_id=test_user.id,
        **complex_data
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    
    # Verify JSON fields are properly serialized
    assert isinstance(profile.dietary_restrictions, list)
    assert len(profile.dietary_restrictions) == 2
    assert "vegan" in profile.dietary_restrictions
