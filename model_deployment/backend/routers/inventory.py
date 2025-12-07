from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
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

# Smart category detection based on common grocery item keywords
def detect_category(item_name: str) -> str:
    """Intelligently categorize grocery items based on keywords."""
    import re
    name = item_name.lower().strip()
    
    def has_word(keywords):
        """Check if any keyword exists as a whole word in name."""
        for kw in keywords:
            # Use word boundary matching to avoid partial matches (e.g., 'ice' in 'rice')
            if re.search(r'\b' + re.escape(kw) + r'\b', name):
                return True
            # Also check if keyword is at start/end (for compound words)
            if name.startswith(kw + ' ') or name.endswith(' ' + kw) or name == kw:
                return True
        return False
    
    # Produce - fruits and vegetables
    produce_keywords = [
        'apple', 'banana', 'orange', 'lemon', 'lime', 'grape', 'berry', 'strawberry',
        'blueberry', 'raspberry', 'mango', 'pineapple', 'watermelon', 'melon', 'peach',
        'pear', 'plum', 'cherry', 'kiwi', 'avocado', 'tomato', 'potato', 'onion',
        'garlic', 'ginger', 'carrot', 'celery', 'broccoli', 'cauliflower', 'spinach',
        'lettuce', 'cabbage', 'kale', 'cucumber', 'pepper', 'zucchini', 'squash',
        'eggplant', 'corn', 'bean', 'pea', 'mushroom', 'asparagus', 'artichoke',
        'beet', 'radish', 'turnip', 'parsley', 'cilantro', 'basil', 'mint', 'herb',
        'salad', 'greens', 'vegetable', 'fruit', 'produce', 'fresh'
    ]
    
    # Dairy products
    dairy_keywords = [
        'milk', 'cream', 'cheese', 'butter', 'yogurt', 'yoghurt', 'cottage', 'ricotta',
        'mozzarella', 'cheddar', 'parmesan', 'feta', 'brie', 'gouda', 'swiss',
        'sour cream', 'half and half', 'creamer', 'whipping', 'ice cream', 'gelato',
        'egg', 'eggs', 'dairy'
    ]
    
    # Meat and proteins
    meat_keywords = [
        'chicken', 'beef', 'pork', 'lamb', 'turkey', 'duck', 'bacon', 'sausage',
        'ham', 'steak', 'ground beef', 'ground turkey', 'meat', 'poultry',
        'fish', 'salmon', 'tuna', 'shrimp', 'prawn', 'lobster', 'crab', 'seafood',
        'tilapia', 'cod', 'halibut', 'trout', 'oyster', 'mussel', 'clam', 'scallop',
        'ribs', 'roast', 'chop', 'filet', 'tenderloin', 'wing', 'thigh', 'breast',
        'deli', 'cold cut', 'salami', 'pepperoni', 'prosciutto'
    ]
    
    # Frozen foods - only if explicitly marked frozen
    frozen_keywords = [
        'frozen', 'freezer', 'frost', 'tv dinner', 'popsicle'
    ]
    
    # Beverages
    beverage_keywords = [
        'water', 'juice', 'soda', 'cola', 'sprite', 'coke', 'pepsi', 'coffee',
        'tea', 'beer', 'wine', 'alcohol', 'drink', 'beverage', 'smoothie',
        'lemonade', 'iced tea', 'energy drink', 'gatorade', 'sparkling', 'mineral'
    ]
    
    # Check frozen first (only explicit frozen items)
    if has_word(frozen_keywords):
        return 'frozen'
    
    # Check ice cream specifically for dairy
    if 'ice cream' in name:
        return 'dairy'
    
    # Check beverages before other categories (juice, etc.)
    if has_word(beverage_keywords):
        return 'beverages'
    
    if has_word(dairy_keywords):
        return 'dairy'
    
    if has_word(meat_keywords):
        return 'meat'
    
    if has_word(produce_keywords):
        return 'produce'
    
    # Default to pantry for dry goods, canned items, etc.
    return 'pantry'


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
    item_name = item["item_name"]
    category = item.get("category") or detect_category(item_name)  # Smart fallback
    
    new_item = InventoryItem(
        user_id=current_user.id,
        item_name=item_name,
        quantity=item["quantity"],
        unit=item["unit"],
        category=category
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

@router.put("/{item_id}")
def update_inventory_item(
    item_id: int,
    item: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.item_name = item.get("item_name", db_item.item_name)
    if "quantity" in item:
        db_item.quantity = float(item["quantity"])
    db_item.unit = item.get("unit", db_item.unit)
    db_item.category = item.get("category", db_item.category)
    db.commit()
    db.refresh(db_item)
    return {"status": "success", "item": {
        "id": db_item.id,
        "item_name": db_item.item_name,
        "quantity": db_item.quantity,
        "unit": db_item.unit,
        "category": db_item.category,
    }}

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
                    "category": detect_category(item_name)  # Smart category detection
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
