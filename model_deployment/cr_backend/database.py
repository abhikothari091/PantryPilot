"""
MongoDB database handler for inventory and preferences
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
import json
from pathlib import Path


class Database:
    def __init__(self, connection_string: str = "mongodb://localhost:27017"):
        """Initialize MongoDB connection"""
        self.connection_string = connection_string
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.connection_string)
        self.db = self.client.pantrypilot

        # Test connection
        await self.client.server_info()
        print(f"✅ Connected to MongoDB at {self.connection_string}")

    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

    async def init_demo_inventory(self):
        """Initialize demo inventory if empty"""
        # Check if inventory exists
        count = await self.db.inventory.count_documents({})

        if count == 0:
            # Load demo inventory
            demo_items = [
                {"name": "chicken breast", "quantity": 2, "unit": "lbs"},
                {"name": "eggs", "quantity": 12, "unit": "count"},
                {"name": "milk", "quantity": 1, "unit": "gallon"},
                {"name": "cheese", "quantity": 8, "unit": "oz"},
                {"name": "pasta", "quantity": 1, "unit": "lb"},
                {"name": "tomatoes", "quantity": 4, "unit": "count"},
                {"name": "onions", "quantity": 3, "unit": "count"},
                {"name": "garlic", "quantity": 1, "unit": "bulb"},
                {"name": "olive oil", "quantity": 16, "unit": "oz"},
                {"name": "rice", "quantity": 2, "unit": "lbs"},
                {"name": "bell peppers", "quantity": 3, "unit": "count"},
                {"name": "carrots", "quantity": 5, "unit": "count"},
                {"name": "potatoes", "quantity": 5, "unit": "count"},
                {"name": "ground beef", "quantity": 1, "unit": "lb"},
                {"name": "salmon fillet", "quantity": 1, "unit": "lb"},
                {"name": "soy sauce", "quantity": 8, "unit": "oz"},
                {"name": "basil", "quantity": 1, "unit": "bunch"},
                {"name": "lemon", "quantity": 3, "unit": "count"},
                {"name": "butter", "quantity": 8, "unit": "oz"},
                {"name": "flour", "quantity": 5, "unit": "lbs"},
            ]

            await self.db.inventory.insert_many(demo_items)
            print(f"✅ Initialized demo inventory with {len(demo_items)} items")

        # Initialize default preferences if not exists
        pref_count = await self.db.preferences.count_documents({})
        if pref_count == 0:
            default_prefs = {
                "dietary_restrictions": [],
                "cooking_style": "balanced",
                "custom_preferences": ""
            }
            await self.db.preferences.insert_one(default_prefs)
            print("✅ Initialized default preferences")

    async def get_inventory(self) -> List[Dict]:
        """Get all inventory items"""
        cursor = self.db.inventory.find({}, {"_id": 0})
        items = await cursor.to_list(length=100)
        return items

    async def add_inventory_item(self, item: Dict) -> Dict:
        """Add or update inventory item"""
        # Check if item already exists
        existing = await self.db.inventory.find_one({"name": item["name"]})

        if existing:
            # Update existing item
            await self.db.inventory.update_one(
                {"name": item["name"]},
                {"$set": item}
            )
        else:
            # Insert new item
            result = await self.db.inventory.insert_one(item)
            # Remove _id from returned item (not JSON serializable)
            item.pop("_id", None)

        return item

    async def remove_inventory_item(self, item_name: str):
        """Remove item from inventory"""
        await self.db.inventory.delete_one({"name": item_name})

    async def get_preferences(self) -> Dict:
        """Get user preferences"""
        prefs = await self.db.preferences.find_one({}, {"_id": 0})
        if not prefs:
            # Return defaults if not found
            prefs = {
                "dietary_restrictions": [],
                "cooking_style": "balanced",
                "custom_preferences": ""
            }
        return prefs

    async def update_preferences(self, preferences: Dict) -> Dict:
        """Update user preferences"""
        # Upsert preferences
        await self.db.preferences.delete_many({})  # Simple single-user approach
        result = await self.db.preferences.insert_one(preferences)
        # Remove _id from returned preferences (not JSON serializable)
        preferences.pop("_id", None)
        return preferences
