import google.generativeai as genai
from PIL import Image
import io
import json
import os
import time
from datetime import datetime


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_from_bytes(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    model = genai.GenerativeModel('gemini-2.5-flash')

    categories = ['protein', 'condiments_spices', 'canned', 'snacks', 'produce', 'dairy', 'grain', 'others']
    
    prompt = f"""Extract all food/grocery items from this receipt.
    Return ONLY valid JSON array:
    [{{"item": "item name", "quantity": "quantity (oz, lbs, etc.)", "category": "one of {categories}"}}]
    Please remove brand names from the item names.
    If the quantity is not given, make an estimate in the appropriate units.
    Categorize each item into one of the following categories: {categories}.
    No explanation, just JSON."""
    
    response = model.generate_content([prompt, img])
    
    text = response.text.strip()
    if text.startswith('```json'):
        text = text.replace('```json', '').replace('```', '').strip()
    
    items = json.loads(text)

    today = datetime.today().strftime("%Y-%m-%d")
    for item in items:
        item["purchase_date"] = today

    return items