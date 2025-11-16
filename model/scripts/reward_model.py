import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer
import random
from typing import List, Dict, Tuple, Optional

# --- 1. Data Loading and Preparation ---

class PreferenceDataset(Dataset):
    """
    PyTorch Dataset to handle recipe preference triplets (request, chosen, rejected).
    Each item is a tuple (request_text, chosen_recipe_text, rejected_recipe_text).
    """
    def __init__(self, preference_triplets: List[Tuple[Dict, Dict, Dict]]):
        self.preference_triplets = preference_triplets
        self.formatter = self._format_recipe_as_text # Use the class's own formatter

    def __len__(self):
        return len(self.preference_triplets)

    def __getitem__(self, idx: int) -> Tuple[str, str, str]:
        original_request, chosen_recipe, rejected_recipe = self.preference_triplets[idx]
        
        # Convert recipe dictionary to a single string for embedding
        # Format request only for request_text
        request_text = self.formatter(recipe={}, request=original_request)
        # Format recipe with its context for chosen/rejected texts
        chosen_text = self.formatter(recipe=chosen_recipe, request=original_request)
        rejected_text = self.formatter(recipe=rejected_recipe, request=original_request)
        
        return request_text, chosen_text, rejected_text

    def _format_recipe_as_text(self, recipe: Dict, request: Optional[Dict] = None) -> str:
        """Combines key recipe fields and optionally request fields into a single string."""
        parts = []
        
        # Add request context if available and not empty
        if request:
            inventory_items = ", ".join([f"{item['item']}: {item['qty']}" for item in request.get("inventory", [])])
            dietary_pref = request.get("dietary_preference", "any")
            parts.append(f"Request: Inventory: {inventory_items} Dietary: {dietary_pref}. ")
        
        # Add recipe details if available and not empty
        if recipe:
            ingredients = ", ".join(recipe.get("ingredients", []))
            steps = recipe.get("steps", "")
            parts.append(f"Recipe: Name: {recipe.get('name', '')} Cuisine: {recipe.get('cuisine', '')} Ingredients: {ingredients} Steps: {steps}.")
        
        return "".join(parts).strip()


def load_preference_data(feedback_file_path: str) -> List[Tuple[Dict, Dict, Dict]]:
    """
    Loads preference data from a .jsonl file containing (user_request, chosen_recipe, rejected_recipe) triplets.

    Args:
        feedback_file_path: Path to the .jsonl file containing user feedback.

    Returns:
        A list of tuples, where each tuple contains an original request dict,
        a chosen recipe dict, and a rejected recipe dict.
    """
    preference_triplets = []
    print(f"load_preference_data: Processing feedback file: {feedback_file_path}")

    if not os.path.exists(feedback_file_path):
        print(f"load_preference_data: Feedback file not found: {feedback_file_path}")
        return []

    with open(feedback_file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            try:
                data = json.loads(line)
                
                user_request = data.get("user_request", "")
                chosen_recipe = data.get("chosen_recipe", {})
                rejected_recipe = data.get("rejected_recipe", {})

                if user_request and chosen_recipe and rejected_recipe:
                    # Format original_request_dict for consistency with _format_recipe_as_text
                    original_request_dict = {"user_query": user_request}
                    preference_triplets.append((original_request_dict, chosen_recipe, rejected_recipe))
                else:
                    print(f"load_preference_data: WARNING: Skipping incomplete feedback entry on line {line_num} in {feedback_file_path}.")
            except json.JSONDecodeError:
                print(f"load_preference_data: Skipping malformed line {line_num} in {feedback_file_path}")
                continue
    
    print(f"load_preference_data: Finished processing. Total preference triplets loaded: {len(preference_triplets)}")
    return preference_triplets

# --- 2. Feature Extraction ---

class RecipeEmbedder:
    """
    Handles converting recipe text into numerical embeddings.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        print(f"SentenceTransformer model loaded on {self.device}.")

    def embed(self, texts: List[str]) -> torch.Tensor:
        """
        Generates embeddings for a list of recipe texts.
        """
        return self.model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

# --- 3. Reward Model Architecture ---

class RewardModel(nn.Module):
    """
    A simple neural network to predict a reward score for a (request, recipe) embedding.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 128): # input_dim will be 2 * original_embedding_dim
        super(RewardModel, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1) # Output a single scalar reward value
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)

# --- 4. Training Logic ---

def train_reward_model(
    data_path: str,
    model_save_path: str = os.path.join(os.path.dirname(__file__), '..', 'backend', 'reward_model.pth'),
    epochs: int = 10,
    lr: float = 1e-4,
    batch_size: int = 4,
    validation_split: float = 0.2 # New parameter for validation split
):
    """
    Main function to orchestrate the training of the reward model.
    """
    print("--- Starting Reward Model Training ---")
    
    # Load data
    preference_triplets = load_preference_data(data_path)
    if not preference_triplets:
        print("No preference data found. Aborting training.")
        return
    print(f"Loaded {len(preference_triplets)} preference triplets.")
    
    # Split data into training and validation sets
    random.shuffle(preference_triplets) # Shuffle before splitting
    split_idx = int(len(preference_triplets) * (1 - validation_split))
    train_triplets = preference_triplets[:split_idx]
    val_triplets = preference_triplets[split_idx:]

    if not train_triplets:
        print("No training data after split. Aborting training.")
        return
    if not val_triplets:
        print("No validation data after split. Skipping validation accuracy calculation.")
    
    train_dataset = PreferenceDataset(train_triplets)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    val_dataset = PreferenceDataset(val_triplets)
    val_dataloader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False) # No need to shuffle validation

    # Initialize models
    embedder = RecipeEmbedder()
    original_embedding_dim = embedder.model.get_sentence_embedding_dimension()
    reward_model_input_dim = original_embedding_dim * 2 
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reward_model = RewardModel(input_dim=reward_model_input_dim).to(device)
    
    optimizer = optim.Adam(reward_model.parameters(), lr=lr)
    loss_fn = nn.MarginRankingLoss(margin=1.0)
    
    print(f"Training for {epochs} epochs on {device}...")
    
    reward_model.train()
    for epoch in range(epochs):
        total_loss = 0
        for request_texts, chosen_texts, rejected_texts in train_dataloader: # Use train_dataloader
            optimizer.zero_grad()
            
            request_embeddings = embedder.embed(list(request_texts)).to(device).clone().detach().requires_grad_(True)
            chosen_recipe_embeddings = embedder.embed(list(chosen_texts)).to(device).clone().detach().requires_grad_(True)
            rejected_recipe_embeddings = embedder.embed(list(rejected_texts)).to(device).clone().detach().requires_grad_(True)
            
            chosen_combined_embeddings = torch.cat((request_embeddings, chosen_recipe_embeddings), dim=1)
            rejected_combined_embeddings = torch.cat((request_embeddings, rejected_recipe_embeddings), dim=1)
            
            chosen_scores = reward_model(chosen_combined_embeddings)
            rejected_scores = reward_model(rejected_combined_embeddings)
            
            target = torch.ones(chosen_scores.size(0), 1).to(device)
            
            loss = loss_fn(chosen_scores, rejected_scores, target)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(train_dataloader) # Use train_dataloader for avg_loss
        print(f"Epoch {epoch+1}/{epochs}, Average Training Loss: {avg_loss:.4f}") # Changed print statement
        
        # --- Validation ---
        if val_triplets:
            reward_model.eval() # Set model to evaluation mode
            correct_predictions = 0
            total_predictions = 0
            with torch.no_grad():
                for request_texts, chosen_texts, rejected_texts in val_dataloader: # Use val_dataloader
                    request_embeddings = embedder.embed(list(request_texts)).to(device)
                    chosen_recipe_embeddings = embedder.embed(list(chosen_texts)).to(device)
                    rejected_recipe_embeddings = embedder.embed(list(rejected_texts)).to(device)
                    
                    chosen_combined_embeddings = torch.cat((request_embeddings, chosen_recipe_embeddings), dim=1)
                    rejected_combined_embeddings = torch.cat((request_embeddings, rejected_recipe_embeddings), dim=1)
                    
                    chosen_scores = reward_model(chosen_combined_embeddings)
                    rejected_scores = reward_model(rejected_combined_embeddings)
                    
                    correct_predictions += torch.sum(chosen_scores > rejected_scores).item()
                    total_predictions += chosen_scores.size(0)
            
            accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
            print(f"Epoch {epoch+1}/{epochs}, Validation Accuracy: {accuracy:.4f}")
            reward_model.train() # Set model back to training mode
        
    # Save the trained model
    torch.save(reward_model.state_dict(), model_save_path)
    print(f"--- Training Complete. Model saved to {model_save_path} ---")


# --- 5. Inference/Prediction ---

def predict_best_recipe(
    recipes: List[Dict],
    original_request: Dict, # Added original_request
    model_path: str = os.path.join(os.path.dirname(__file__), '..', 'backend', 'reward_model.pth')
) -> Dict:
    """
    Given a list of recipes, uses the trained reward model to predict the best one.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Load the trained model
    embedder = RecipeEmbedder()
    embedding_dim = embedder.model.get_sentence_embedding_dimension()
    reward_model = RewardModel(input_dim=embedding_dim * 2) # Input dim is now 2x
    reward_model.load_state_dict(torch.load(model_path))
    reward_model.to(device)
    reward_model.eval()

    # Prepare recipe texts and request text
    # Use the _format_recipe_as_text from PreferenceDataset for consistency
    # Create a dummy dataset instance to access the formatter
    dummy_dataset = PreferenceDataset([]) 
    
    scored_recipes = []
    with torch.no_grad():
        for recipe in recipes:
            request_text = dummy_dataset.formatter(recipe={}, request=original_request)
            recipe_text = dummy_dataset.formatter(recipe=recipe, request=original_request)
            
            request_embedding = embedder.embed([request_text]).to(device)
            recipe_embedding = embedder.embed([recipe_text]).to(device)
            
            combined_embedding = torch.cat((request_embedding, recipe_embedding), dim=1)
            score = reward_model(combined_embedding).item()
            scored_recipes.append((score, recipe))
    
    # Sort by score in descending order
    scored_recipes.sort(key=lambda x: x[0], reverse=True)
    
    return scored_recipes[0][1] # Return the best recipe


if __name__ == '__main__':
    # This block shows how to run the training.
    # The user_data directory is expected to be at ../user_data relative to this script.
    FEEDBACK_FILE_PATH = os.path.join(
        os.path.dirname(__file__), # This script's directory
        '..', 'user_data', 'my_preferences.jsonl'
    )
    
    print(f"Checking for feedback data in: {FEEDBACK_FILE_PATH}")
    if os.path.exists(FEEDBACK_FILE_PATH):
        print("Found feedback data. Proceeding with training.")
        train_reward_model(
            data_path=FEEDBACK_FILE_PATH, 
            model_save_path=os.path.join(os.path.dirname(__file__), '..', 'backend', 'reward_model.pth')
        )
    else:
        print(f"Feedback data file does not exist: {FEEDBACK_FILE_PATH}")
        print("Skipping training. Please generate some preference data first by using the API.")
