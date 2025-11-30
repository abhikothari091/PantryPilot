# 🍳 PantryPilot Web Application

The **PantryPilot Web App** is a production-ready interface designed to demonstrate the capabilities of the fine-tuned Llama 3.2 3B model. It provides a seamless user experience for inventory management and personalized recipe generation, bridging the gap between raw model inference and practical utility.

---

## 🏗️ System Architecture

The application follows a modern decoupled architecture, separating the UI from the inference engine and database.

```mermaid
graph TD
    User[User] -->|Interacts| UI[React Frontend]
    UI -->|HTTP Requests| API[FastAPI Backend]
    
    subgraph Backend Services
        API -->|Auth & Data| DB[(NeonDB PostgreSQL)]
        API -->|Inference| Model[Model Service]
        Model -->|Loads| LoRA[LoRA Adapter]
        Model -->|Loads| Base[Llama 3.2 3B]
    end
    
    subgraph Logic Layer
        API -->|Deduction| SmartInv[Smart Inventory Utility]
        SmartInv -->|Updates| DB
    end
```

### Data Flow
1.  **User Request**: User inputs a query (e.g., "Dinner") and selects servings (e.g., 2).
2.  **Context Assembly**: Backend fetches user's **Inventory** and **Dietary Preferences** from NeonDB.
3.  **Prompt Engineering**: `ModelService` constructs a structured prompt combining:
    *   System instructions (JSON schema enforcement).
    *   Inventory list (formatted string).
    *   User constraints (servings, cuisine).
4.  **Inference**: The fine-tuned Llama 3.2 model generates a recipe JSON.
5.  **Inventory Update**: When marked as "Cooked", the **Smart Inventory Utility** parses ingredients, converts units, and deducts quantities from the database.

---

## 🧠 Backend Deep Dive (`backend/`)

The backend is built with **FastAPI** for high performance and easy async handling of model inference.

### 1. Model Service (`model_service.py`)
This singleton class manages the lifecycle of the LLM.

*   **Loading**: Uses `peft` to load the LoRA adapter on top of `meta-llama/Llama-3.2-3B-Instruct`.
*   **Device Management**: Automatically selects `mps` (Mac), `cuda` (NVIDIA), or `cpu`.
*   **Prompt Formatting**:
    ```python
    # Example Prompt Structure
    <|im_start|>system
    You are a helpful cooking assistant... Output JSON only...
    <|im_end|>
    <|im_start|>user
    Inventory: 2 lbs Chicken, 5 Tomatoes...
    Request: Quick dinner for 2 servings...
    <|im_end|>
    ```
*   **Generation**: Uses `temperature=0.7` for creativity balanced with instruction adherence.

### 2. Smart Inventory Deduction (`utils/smart_inventory.py`)
A robust utility module designed to handle the messiness of real-world data.

*   **Ingredient Parsing**: Uses Regex (`r"([\d\.\/]+)\s*([a-zA-Z]+)?\s+(.*)"`) to extract:
    *   Quantity (handles decimals `1.5` and fractions `1/2`)
    *   Unit (e.g., "lbs", "tablespoon")
    *   Item Name (e.g., "Chicken Breast")
*   **Unit Normalization**: Maps variations to standard keys:
    *   `pounds`, `lb`, `lbs` → `lb`
    *   `tablespoon`, `tbsp` → `tbsp`
*   **Unit Conversion**:
    *   **Weight**: Converts between `g`, `kg`, `lb`, `oz`. (e.g., 16 oz == 1 lb).
    *   **Volume**: Converts between `ml`, `l`, `cup`, `tbsp`, `tsp`.
*   **Fuzzy Matching**:
    *   Handles Singular/Plural: "Tomato" matches "Tomatoes".
    *   Substring Matching: "Chicken" matches "Boneless Chicken Breast".

### 3. API Endpoints (`routers/`)

| Method | Endpoint | Description | Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/recipes/generate` | Generates a recipe | `{"user_request": "...", "servings": 2}` |
| `POST` | `/recipes/{id}/cooked` | Marks cooked & deducts inventory | None |
| `GET` | `/inventory` | Lists user's pantry | None |
| `POST` | `/inventory/upload` | OCR receipt processing | `Multipart Form Data (Image)` |

---

## 🎨 Frontend Deep Dive (`frontend/`)

The frontend is a **React** Single Page Application (SPA) built with **Vite**.

### Key Components

*   **`RecipeGenerator.jsx`**: The core experience.
    *   **State**: Manages `query`, `servings`, `loading`, and `recipe` data.
    *   **Animations**: Uses `framer-motion` for the spinning chef hat and fading transitions.
    *   **Rendering**: Parses the raw JSON response to render structured lists (Ingredients, Steps).
*   **`Dashboard.jsx`**: Inventory management center.
    *   **OCR Integration**: Handles file uploads and displays a scanning animation while the backend processes the receipt.
    *   **Real-time Updates**: Refetches inventory immediately after adding items or cooking.

### UI/UX Design Choices
*   **Tailwind CSS**: Used for rapid, utility-first styling.
*   **Glassmorphism**: Subtle transparencies and blurs for a modern, premium feel.
*   **Feedback Loops**:
    *   Loading states clearly indicate "Crafting recipe..." or "Scanning receipt...".
    *   Success notifications when inventory is updated.

---

## 🚀 Setup & Deployment Guide

### Prerequisites
*   **Python 3.9+**
*   **Node.js 16+**
*   **PostgreSQL Database** (NeonDB recommended)
*   **Hugging Face Account** (for Llama 3.2 access)

### 1. Backend Installation

```bash
cd model_deployment/backend

# 1. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install Dependencies
pip install -r requirements.txt
# Note: Ensure torch is installed with CUDA support if using NVIDIA GPU

# 3. Environment Configuration
# Create a .env file
echo "DATABASE_URL=postgresql://user:pass@host/db?sslmode=require" > .env
echo "HF_TOKEN=your_hf_token_here" >> .env

# 4. Run Server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Installation

```bash
cd model_deployment/frontend

# 1. Install Dependencies
npm install

# 2. Run Development Server
npm run dev
```

---

## 🧪 Testing & Verification

### Scenario A: The "Chicken Dinner" Flow
**Goal**: Verify recipe generation and smart inventory deduction.

1.  **Setup**: Ensure your inventory has **"Boneless chicken breast"** (Quantity: 2.5 lbs).
2.  **Generate**:
    *   Go to **Recipe Generator**.
    *   Set Servings: **1**.
    *   Request: **"Simple Chicken Breast"**.
3.  **Verify Output**:
    *   The model should generate a recipe using "Chicken Breast".
    *   Check the ingredients list for a quantity (e.g., "8 oz" or "0.5 lbs").
4.  **Cook**: Click **"Mark as Cooked"**.
5.  **Verify Deduction**:
    *   Go to **Dashboard**.
    *   Check "Boneless chicken breast".
    *   **Expected**: 2.5 lbs - 0.5 lbs (8 oz) = **2.0 lbs**.

### Scenario B: OCR Receipt Scanning
**Goal**: Verify image processing and inventory population.

1.  **Upload**: On the Dashboard, click "Upload Receipt".
2.  **Select**: Choose a sample receipt image (e.g., from `model_development/ocr/test_receipts/`).
3.  **Animation**: Verify the "Scanning..." animation appears.
4.  **Result**: Confirm the detected items are added to your inventory list.

---

## 🔧 Troubleshooting

| Issue | Possible Cause | Solution |
| :--- | :--- | :--- |
| **Model Load Error** | Missing `HF_TOKEN` or gated access | Ensure you accepted Llama 3.2 terms on Hugging Face and set `HF_TOKEN`. |
| **Inventory Not Deducting** | Unit mismatch (e.g., "can" vs "lbs") | The system falls back to simple count deduction (1 unit/serving) if units are incompatible. |
| **CORS Error** | Frontend/Backend port mismatch | Ensure Backend allows `http://localhost:5173` in `main.py` CORS settings. |
| **Database Error** | Missing `servings` column | Run the migration script or use the `/fix_db` endpoint if provided in dev tools. |
