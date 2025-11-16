# Personalized Recipe Reward Model

This document outlines the architecture, status, and usage of the machine learning models for the PantryPilot project, focusing on the personalized reward model.

## 1. Overview

This system uses two main models:
1.  **Generator Model:** A fine-tuned Llama 3.2 3B model (`model/generator/`) that creates recipes based on a user's inventory and preferences.
2.  **Reward Model:** A PyTorch-based feed-forward neural network that learns a user's recipe preferences. It is trained on pairs of recipes (one chosen, one rejected) to predict which recipe a user will prefer.

The goal is to use the Reward Model to rank recipes from the Generator Model and serve the user the best possible option.

## 2. Current Status & Known Issues

*   **Generator Pipeline: Healthy.** The generator model is producing diverse recipes.
*   **Reward Model: NOT VIABLE FOR PRODUCTION.** The model is not robust enough for practical use.
    *   **Identical Scores Problem:** The model often produces the exact same score for different, complex recipes. This is likely due to a "collapse" where it outputs a default score for any input it doesn't recognize from its limited training data.
    *   **Reason:** The model was trained on a very small, manually-created dataset of only 43 preference pairs. While it achieved **88.89% validation accuracy** on this small set, it is not sufficient for generalizing to real-world recipes.

The main backend API (`model/backend/main.py`) **does not currently use the reward model for ranking** due to this issue. We will integrate the reward model into the main application flow over time as we collect more user preference data via the API.

## 3. Architecture & Setup

### Components
*   `model/backend/`: FastAPI backend that serves the models.
*   `model/generator/`: The fine-tuned Llama 3.2 recipe generation model.
*   `model/scripts/`: Contains scripts for training, debugging, and testing the models.
*   `model/user_data/`: Contains user preference data used for training the reward model.
*   `model/backend/reward_model.pth`: The currently trained reward model weights.

### Setup
1.  Install the required Python packages from the root directory:
    ```bash
    pip install -r requirements.txt
    ```
2.  Ensure you have an Ollama instance running and accessible at `http://localhost:11434`.

## 4. How to Use

### Training the Reward Model
To retrain the reward model with new data from `model/user_data/my_preferences.jsonl`:

1.  **Run the training script from the project's root directory:**
    ```bash
    python model/scripts/reward_model.py
    ```
2.  The script will automatically use the data from `model/user_data/my_preferences.jsonl`, train the model, and save the updated weights to `model/backend/reward_model.pth`.

3.  **Training Hyperparameters:** The initial 88.89% accuracy was achieved with the following default parameters:
    *   **Epochs:** `10`
    *   **Learning Rate:** `1e-4`
    *   **Batch Size:** `4`
    *   **Validation Split:** `0.2`

### Running the Backend Server
The main application is served via a FastAPI backend. The `recipe_endpoints.py` script includes the experimental re-ranking logic.

1.  **Run the server from the project's root directory:**
    ```bash
    python model/scripts/recipe_endpoints.py
    ```
2.  The API will be available at `http://localhost:8000`. You can access the health check at `http://localhost:8000/health`.

## 5. Next Steps

The primary goal is to **train a better reward model**. This requires a larger and more diverse dataset of preference pairs.

1.  **Option A (Manual & Personalized):** Manually create more high-quality preference pairs in `my_preferences.jsonl` (aiming for 100-200+) to build a stronger, personalized model.
2.  **Option B (Synthetic & Generic):** Build a data generation pipeline to create a large, synthetic preference dataset from the existing `chat_format` or `recipes_15k_raw.jsonl` files.