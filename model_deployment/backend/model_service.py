"""
External API Model Service
Replaces local Llama 3B model with external API call
"""

import requests
import json
from typing import List, Dict, Optional
import os

class ModelService:
    def __init__(self):
        """
        Initialize model service for external API
        """
        self.api_url = "https://pantrypilot-llm-885773477836.us-central1.run.app/api/generate-recipe"
        print(f"🔗 Initialized External Model Service: {self.api_url}")

    def generate_recipe(
        self,
        inventory: List[Dict],
        preferences: Dict,
        user_request: str = "",
        use_finetuned: bool = True, # Kept for compatibility signature
        max_tokens: int = 512,      # Kept for compatibility signature
        temperature: float = 0.7,   # Kept for compatibility signature
        top_p: float = 0.9          # Kept for compatibility signature
    ) -> str:
        """
        Generate a recipe using external API
        
        Args:
            inventory: List of available ingredients
            preferences: User preferences including dietary restrictions
            user_request: Optional natural language request
            
        Returns:
            Generated recipe text (JSON string)
        """
        print(f"🚀 Calling external API for: {user_request}")
        
        # Map preferences to API format
        # Local preferences: {"dietary_restrictions": [...], "allergies": [...], "favorite_cuisines": [...]}
        # API preferences: {"dietary_restrictions": [], "cooking_style": "balanced", "custom_preferences": ""}
        
        api_preferences = {
            "dietary_restrictions": preferences.get("dietary_restrictions", []),
            "cooking_style": "balanced", # Default
            "custom_preferences": ""
        }
        
        # Add allergies to custom preferences if present
        if preferences.get("allergies"):
            allergies = ", ".join(preferences["allergies"])
            api_preferences["custom_preferences"] += f" Allergies: {allergies}."
            
        # Add favorite cuisines to custom preferences
        if preferences.get("favorite_cuisines"):
            cuisines = ", ".join(preferences["favorite_cuisines"])
            api_preferences["custom_preferences"] += f" Favorite cuisines: {cuisines}."
            
        # Append instruction for detailed steps to the user request
        detailed_request = f"{user_request} Please provide detailed, step-by-step cooking instructions."

        payload = {
            "user_request": detailed_request,
            "inventory": inventory, # Expected format: [{"name": "chicken", ...}, ...] - matches local
            "preferences": api_preferences,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # The API returns structured JSON. We need to return it as a string 
            # because the router expects a string (which it then tries to parse).
            # To be safe and compatible with the router's new robust parsing logic,
            # we can return it as a JSON string.
            
            # The API returns: {"recipe": {"status": "ok", "recipe": {...}}, "base_recipe": null}
            # The frontend expects: {"status": "ok", "recipe": {...}} (which allows parsed.recipe to access the inner recipe)
            # So we extract data["recipe"]
            
            if "recipe" in data:
                return json.dumps(data["recipe"])
            else:
                return json.dumps(data)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API Request failed: {e}")
            return json.dumps({
                "raw_text": f"Sorry, I couldn't generate a recipe at this time. Error: {str(e)}"
            })

    def generate_comparison(
        self,
        inventory: List[Dict],
        preferences: Dict,
        user_request: str = "",
        max_tokens: int = 512
    ) -> Dict[str, str]:
        """
        Generate recipes comparison (Mocked for external API)
        """
        # For now, just return the same recipe for both or handle as needed.
        # Since the external API doesn't support comparison explicitly in the same way,
        # we'll just generate one recipe.
        
        recipe = self.generate_recipe(inventory, preferences, user_request)
        
        return {
            "base": recipe,
            "finetuned": recipe
        }

    def cleanup(self):
        """No-op for API service"""
        pass


# Global model instance
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """Get or create global model service instance"""
    global _model_service

    if _model_service is None:
        _model_service = ModelService()

    return _model_service
