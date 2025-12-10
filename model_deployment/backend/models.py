from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    inventory = relationship("InventoryItem", back_populates="user")
    recipe_history = relationship("RecipeHistory", back_populates="user")
    preferences = relationship("RecipePreference", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    dietary_restrictions = Column(JSON, default=list) # e.g. ["vegan", "gluten-free"]
    allergies = Column(JSON, default=list) # e.g. ["peanuts"]
    favorite_cuisines = Column(JSON, default=list) # e.g. ["Italian", "Chinese"]
    recipe_generation_count = Column(Integer, default=0)
    
    user = relationship("User", back_populates="profile")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    item_name = Column(String, index=True)
    quantity = Column(Float)
    unit = Column(String) # e.g. "kg", "pcs", "oz"
    expiry_date = Column(DateTime, nullable=True)
    category = Column(String, nullable=True) # e.g. "produce", "dairy"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="inventory")

class RecipeHistory(Base):
    __tablename__ = "recipe_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    recipe_json = Column(JSON) # The full generated recipe
    raw_response = Column(String, nullable=True) # Raw LLM response text
    user_query = Column(String)
    servings = Column(Integer, default=2)
    feedback_score = Column(Integer, default=0) # 0=None, 1=Dislike, 2=Like
    is_cooked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recipe_history")

class RecipePreference(Base):
    __tablename__ = "recipe_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_query = Column(String, nullable=True)
    servings = Column(Integer, nullable=True)
    generation_number = Column(Integer, nullable=True)
    prompt = Column(String, nullable=False)
    variant_a = Column(JSON, nullable=False)
    variant_b = Column(JSON, nullable=False)
    variant_a_raw = Column(String, nullable=True)
    variant_b_raw = Column(String, nullable=True)
    chosen_variant = Column(String, nullable=True) # "A" or "B"
    rejected_variant = Column(String, nullable=True)
    chosen_recipe_history_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    chosen_at = Column(DateTime, nullable=True)
    skipped = Column(Boolean, nullable=True)
    exported_for_training = Column(Boolean, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")


class RetrainingNotification(Base):
    """
    Tracks retraining notifications to avoid duplicate alerts.
    """

    __tablename__ = "retraining_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    preference_count = Column(Integer, nullable=False)
    satisfaction_ratio = Column(Float, nullable=False)
    notified_at = Column(DateTime, default=datetime.utcnow)
    approved = Column(Boolean, default=False)
    training_started = Column(Boolean, default=False)
