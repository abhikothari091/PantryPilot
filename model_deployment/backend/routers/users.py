from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from database import get_db
from models import UserProfile, User
from routers.inventory import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

class UserProfileUpdate(BaseModel):
    dietary_restrictions: List[str]
    allergies: List[str]
    favorite_cuisines: List[str]

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        # Should exist if created on register, but just in case
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return {
        "username": current_user.username,
        "email": current_user.email,
        "dietary_restrictions": profile.dietary_restrictions,
        "allergies": profile.allergies,
        "favorite_cuisines": profile.favorite_cuisines
    }

@router.put("/profile")
def update_profile(body: UserProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.dietary_restrictions = body.dietary_restrictions
    profile.allergies = body.allergies
    profile.favorite_cuisines = body.favorite_cuisines
    
    db.commit()
    return {"status": "success", "profile": body}
