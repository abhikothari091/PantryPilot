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
        
        dietary = preferences.get("dietary_restrictions", [])
        allergies = preferences.get("allergies", [])
        cuisines = preferences.get("favorite_cuisines", [])
        
        api_preferences = {
            "dietary_restrictions": dietary,
            "cooking_style": "balanced",
            "custom_preferences": ""
        }
        
        # Build STRICT dietary restrictions message
        strict_restrictions = []
        
        if dietary:
            dietary_str = ", ".join(dietary)
            strict_restrictions.append(f"CRITICAL DIETARY RESTRICTIONS: {dietary_str}")
            
            # Add explicit forbidden ingredients for common restrictions
            if any(d.lower() in ["vegetarian", "vegan"] for d in dietary):
                strict_restrictions.append("ABSOLUTELY NO meat, poultry, fish, or seafood (no chicken, beef, pork, lamb, turkey, salmon, shrimp, etc.)")
            if any(d.lower() == "vegan" for d in dietary):
                strict_restrictions.append("ABSOLUTELY NO animal products (no eggs, dairy, milk, cheese, butter, cream, honey)")
            if any("gluten" in d.lower() for d in dietary):
                strict_restrictions.append("ABSOLUTELY NO gluten (no wheat, barley, rye, regular pasta, bread, flour)")
        
        if allergies:
            allergies_str = ", ".join(allergies)
            strict_restrictions.append(f"SEVERE ALLERGIES - LIFE THREATENING: {allergies_str}")
            strict_restrictions.append(f"NEVER use these allergens: {allergies_str}")
            
        # Add favorite cuisines as a preference (not restriction)
        if cuisines:
            api_preferences["custom_preferences"] += f" Preferred cuisines: {', '.join(cuisines)}."
            
        # Build the final request with strict instructions
        restriction_text = ""
        if strict_restrictions:
            restriction_text = "\n\n⚠️ MANDATORY RESTRICTIONS (MUST FOLLOW - NO EXCEPTIONS):\n" + "\n".join(f"• {r}" for r in strict_restrictions) + "\n\nDo NOT suggest any recipe that violates these restrictions. This is non-negotiable.\n\n"
            api_preferences["custom_preferences"] = restriction_text + api_preferences["custom_preferences"]
            
        # Append instruction for detailed steps and strict ingredient usage
        detailed_request = (
            f"{user_request}"
            f"{restriction_text}"
            f"Please provide detailed, step-by-step cooking instructions. "
            "Use only ingredients you list in the recipe; do not include ingredients that are unused or marked as 'ignore'. "
            "Keep the ingredient list tightly aligned to the actual steps."
        )

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
