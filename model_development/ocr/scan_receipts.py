import google.generativeai as genai
from PIL import Image
from io import BytesIO
import json
import os
import time
from datetime import datetime


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def extract_receipt_items(img_path):
    img = Image.open(img_path)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """Extract all food/grocery items from this receipt.
    Return ONLY valid JSON array:
    [{"item": "item name", "quantity": "quantity (oz, lbs, etc.)"}]
    Please remove brand names from the item names.
    If the quantity is not given, make an estimate in the appropriate units.
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

if __name__ == "__main__":
    test_path = "model_development/ocr/test_receipts/r0.jpg"
    print(extract_receipt_items(test_path))

