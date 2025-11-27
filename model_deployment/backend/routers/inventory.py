from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import json
import os

from database import get_db
from models import InventoryItem, User
from routers.auth import verify_password # Not needed here but good to have context
from fastapi.security import OAuth2PasswordBearer
from auth_utils import ALGORITHM, SECRET_KEY
from jose import jwt, JWTError

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.get("/", response_model=List[dict])
def get_inventory(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(InventoryItem).filter(InventoryItem.user_id == current_user.id).all()
    return [{"id": i.id, "item_name": i.item_name, "quantity": i.quantity, "unit": i.unit, "category": i.category} for i in items]

@router.post("/")
def add_inventory_item(item: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # item dict expected: {"item_name": str, "quantity": float, "unit": str, "category": str}
    new_item = InventoryItem(
        user_id=current_user.id,
        item_name=item["item_name"],
        quantity=item["quantity"],
        unit=item["unit"],
        category=item.get("category", "pantry")
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"status": "success", "item_id": new_item.id}

@router.delete("/{item_id}")
def delete_inventory_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"status": "success"}

@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # OCR Logic using external API
    try:
        content = await file.read()
        
        # External OCR API URL
        url = "https://ocr-api-739616330518.us-east1.run.app/extract"
        files = {"file": ("receipt.jpg", content, file.content_type)}
        
        import requests
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            items_data = response.json()
            
            # Handle different response formats
            if isinstance(items_data, str):
                # If response is a string, try to parse as JSON
                try:
                    import json as json_lib
                    items_data = json_lib.loads(items_data)
                except:
                    return {"status": "error", "message": "OCR returned invalid format"}
            
            # Ensure items_data is a list
            if isinstance(items_data, dict):
                # If it's a dict, try to extract items array
                items = items_data.get('items', items_data.get('detected_items', [items_data]))
            elif isinstance(items_data, list):
                items = items_data
            else:
                return {"status": "error", "message": f"Unexpected OCR response format: {type(items_data)}"}
            
            # The API returns [{"item": "name", "quantity": "qty"}] or similar
            # We need to map it to our schema: item_name, quantity, unit, category
            detected_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                # Simple parsing logic
                qty_str = item.get("quantity", item.get("qty", "1 pcs"))
                # Try to extract number and unit
                import re
                match = re.match(r"([\d\.]+)\s*(.*)", str(qty_str))
                if match:
                    qty = float(match.group(1))
                    unit = match.group(2).strip() or "pcs"
                else:
                    qty = 1.0
                    unit = "pcs"
                
                item_name = item.get("item", item.get("name", item.get("item_name", "Unknown Item")))
                
                detected_items.append({
                    "item_name": item_name,
                    "quantity": qty,
                    "unit": unit if unit else "pcs",
                    "category": "pantry"  # Default
                })
            
            return {"status": "success", "detected_items": detected_items}
        else:
            return {"status": "error", "message": f"OCR API failed: {response.text}"}
        
    except Exception as e:
        import traceback
        return {"status": "error", "message": f"{str(e)} - {traceback.format_exc()}"}

@router.post("/confirm_upload")
def confirm_upload(items: List[dict], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Add multiple items confirmed by user
    for item in items:
        new_item = InventoryItem(
            user_id=current_user.id,
            item_name=item["item_name"],
            quantity=item.get("quantity", 1.0),
            unit=item.get("unit", "pcs"),
            category=item.get("category", "pantry")
        )
        db.add(new_item)
    db.commit()
    return {"status": "success", "count": len(items)}
