"""
Admin router - provides metrics and analytics endpoints.
Restricted to admin users only.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from database import get_db
from models import User, UserProfile, InventoryItem, RecipeHistory, RecipePreference
from dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin username - hardcoded for simplicity
ADMIN_USERNAME = "admin"


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency to check if user is admin."""
    if current_user.username != ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/metrics")
def get_admin_metrics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Get comprehensive dashboard metrics for admin."""
    
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    # === USER METRICS ===
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    # New signups in last 7 days
    new_users_7d = db.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar() or 0
    
    # Active users (generated recipe in last 7 days)
    active_users_7d = db.query(func.count(func.distinct(RecipeHistory.user_id))).filter(
        RecipeHistory.created_at >= seven_days_ago
    ).scalar() or 0
    
    # === RECIPE METRICS ===
    total_recipes = db.query(func.count(RecipeHistory.id)).scalar() or 0
    
    # Recipes in last 7 days
    recipes_7d = db.query(func.count(RecipeHistory.id)).filter(
        RecipeHistory.created_at >= seven_days_ago
    ).scalar() or 0
    
    # Recipes by day for the last 7 days (for chart)
    recipes_by_day = []
    for i in range(7):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(RecipeHistory.id)).filter(
            and_(RecipeHistory.created_at >= day_start, RecipeHistory.created_at < day_end)
        ).scalar() or 0
        recipes_by_day.append({
            "date": day_start.strftime("%b %d"),
            "count": count
        })
    recipes_by_day.reverse()  # Oldest to newest
    
    # Feedback metrics
    recipes_with_feedback = db.query(func.count(RecipeHistory.id)).filter(
        RecipeHistory.feedback_score > 0
    ).scalar() or 0
    
    liked_recipes = db.query(func.count(RecipeHistory.id)).filter(
        RecipeHistory.feedback_score == 2
    ).scalar() or 0
    
    disliked_recipes = db.query(func.count(RecipeHistory.id)).filter(
        RecipeHistory.feedback_score == 1
    ).scalar() or 0
    
    # Cooked recipes
    cooked_recipes = db.query(func.count(RecipeHistory.id)).filter(
        RecipeHistory.is_cooked == True
    ).scalar() or 0
    
    # Calculate rates
    feedback_rate = round((recipes_with_feedback / total_recipes * 100), 1) if total_recipes > 0 else 0
    cook_rate = round((cooked_recipes / total_recipes * 100), 1) if total_recipes > 0 else 0
    like_rate = round((liked_recipes / recipes_with_feedback * 100), 1) if recipes_with_feedback > 0 else 0
    
    # === INVENTORY METRICS ===
    total_inventory_items = db.query(func.count(InventoryItem.id)).scalar() or 0
    
    # Low stock items (quantity < 0.1)
    low_stock_items = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.quantity < 0.1
    ).scalar() or 0
    
    # Popular categories
    category_counts = db.query(
        InventoryItem.category,
        func.count(InventoryItem.id).label('count')
    ).group_by(InventoryItem.category).order_by(func.count(InventoryItem.id).desc()).limit(5).all()
    
    popular_categories = [
        {"category": cat or "Uncategorized", "count": count}
        for cat, count in category_counts
    ]
    
    # === DPO METRICS ===
    total_dpo_comparisons = db.query(func.count(RecipePreference.id)).scalar() or 0
    completed_dpo = db.query(func.count(RecipePreference.id)).filter(
        RecipePreference.chosen_variant != None
    ).scalar() or 0
    skipped_dpo = db.query(func.count(RecipePreference.id)).filter(
        RecipePreference.skipped == True
    ).scalar() or 0
    
    dpo_completion_rate = round((completed_dpo / total_dpo_comparisons * 100), 1) if total_dpo_comparisons > 0 else 0
    
    # === TOP USERS ===
    top_users = db.query(
        User.username,
        func.count(RecipeHistory.id).label('recipe_count')
    ).join(RecipeHistory).group_by(User.id).order_by(
        func.count(RecipeHistory.id).desc()
    ).limit(5).all()
    
    top_users_list = [
        {"username": username, "recipes": count}
        for username, count in top_users
    ]
    
    # === USER GROWTH (last 30 days) ===
    user_growth = []
    for i in range(30):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(User.id)).filter(
            and_(User.created_at >= day_start, User.created_at < day_end)
        ).scalar() or 0
        if i < 7:  # Only include last 7 days in chart
            user_growth.append({
                "date": day_start.strftime("%b %d"),
                "count": count
            })
    user_growth.reverse()
    
    return {
        "timestamp": now.isoformat(),
        "users": {
            "total": total_users,
            "new_7d": new_users_7d,
            "active_7d": active_users_7d,
            "growth_chart": user_growth
        },
        "recipes": {
            "total": total_recipes,
            "last_7d": recipes_7d,
            "by_day": recipes_by_day,
            "feedback_rate": feedback_rate,
            "cook_rate": cook_rate,
            "like_rate": like_rate,
            "liked": liked_recipes,
            "disliked": disliked_recipes,
            "cooked": cooked_recipes
        },
        "inventory": {
            "total_items": total_inventory_items,
            "low_stock": low_stock_items,
            "categories": popular_categories
        },
        "dpo": {
            "total_comparisons": total_dpo_comparisons,
            "completed": completed_dpo,
            "skipped": skipped_dpo,
            "completion_rate": dpo_completion_rate
        },
        "top_users": top_users_list
    }


@router.post("/seed")
def seed_admin_user(db: Session = Depends(get_db)):
    """
    Create admin user if not exists.
    This is a one-time setup endpoint.
    """
    from auth_utils import get_password_hash
    
    # Check if admin already exists
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        return {"message": "Admin user already exists", "created": False}
    
    # Create admin user
    admin_user = User(
        username="admin",
        email="kothari.abhi@northeastern.edu", # Using email from user request implicitly or placeholder
        hashed_password=get_password_hash("Abhi@AK47")
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Create profile
    profile = UserProfile(
        user_id=admin_user.id,
        dietary_restrictions=[],
        allergies=[],
        favorite_cuisines=[]
    )
    db.add(profile)
    db.commit()
    
    return {"message": "Admin user created", "created": True}
