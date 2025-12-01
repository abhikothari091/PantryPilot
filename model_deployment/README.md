# 🍳 PantryPilot – Model Deployment (Web App)

Full-stack web application for PantryPilot, covering auth, profiles, inventory management, OCR receipt ingest, recipe generation, history, cooked deduction, feedback, and optional video generation. Frontend is React/Vite; backend is FastAPI + SQLAlchemy with Postgres (Neon). Deployed on Render as two services (backend Web Service, frontend Static Site). This document is intentionally detailed so a new engineer can deploy, extend, or debug without tribal knowledge.

---

## System Architecture

```mermaid
flowchart LR
    User -->|browser| FE["Frontend (React, Vite, Tailwind)"]
    FE -->|REST + JWT| BE[Backend FastAPI]
    BE -->|SQLAlchemy| DB[(Postgres Neon)]
    BE -->|Recipe API| LLM[External LLM Service]
    BE -->|OCR API| OCR[Receipt OCR Service]
    BE -->|Optional video| VID[Video Gen Veo]
    BE -->|Auth| JWT[JWT Signing SECRET_KEY]
```

### Request Lifecycle (happy path)

1) User authenticates (register/login) → JWT issued and stored client-side.  
2) Inventory/Profiles fetched via authenticated calls.  
3) Recipe generate: frontend posts prompt → backend pulls inventory + profile → calls external model → saves JSON to history → returns recipe.  
4) Cooked: user marks cooked → backend parses ingredients, matches inventory, converts units, deducts quantities.  
5) OCR: user uploads receipt → backend sends to external OCR → user confirms detected items → inserts into inventory.  
6) Video (optional): frontend triggers `/recipes/video` → mock URL unless Veo enabled.

### Backend request flow (recipe generation)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI /recipes/generate
    participant DB as Postgres
    participant LLM as External Recipe API

    FE->>API: POST /recipes/generate (JWT, user_request, servings)
    API->>DB: Query inventory + profile for user
    API->>LLM: Call external recipe service (inventory, preferences, prompt)
    LLM-->>API: JSON/Raw recipe text
    API->>API: Parse JSON (robust fallback to raw_text)
    API->>DB: Insert RecipeHistory (recipe_json, user_query, servings)
    API-->>FE: {status: success, data: recipe, history_id}
```

### Backend request flow (cooked deduction)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI /recipes/{id}/cooked
    participant DB as Postgres

    FE->>API: POST /recipes/{id}/cooked (JWT)
    API->>DB: Load recipe_json + inventory items
    API->>API: Parse ingredients, normalize units, convert quantities
    API->>DB: Deduct quantities (fallback to count when incompatible)
    API-->>FE: {status: success}
```

---

## Components & Technologies

- Frontend: React 19, Vite, Tailwind CSS, framer-motion, axios. Auth via JWT stored locally; API base set by `VITE_API_BASE_URL`. Animations for loading/UX polish.
- Backend: FastAPI, SQLAlchemy, Postgres, passlib + jose (JWT), Pillow (image handling), requests. External calls: recipe model API (Cloud Run), OCR API, optional Veo video gen. CORS configurable via env.
- Data: Postgres tables for users, profiles, inventory, recipe history.

---

## Repository Layout (model_deployment/)

```
model_deployment/
  backend/
    main.py                 # FastAPI app, CORS, startup/shutdown
    routers/                # auth, users, inventory, recipes
      auth.py               # register/login (JWT)
      users.py              # profile CRUD
      inventory.py          # inventory CRUD + OCR upload/confirm
      recipes.py            # recipe gen, cooked, feedback, history, video (mock/live)
    model_service.py        # external recipe API client (LLM)
    utils/smart_inventory.py# ingredient parsing, normalization, unit conversion, fuzzy match
    models.py               # SQLAlchemy models (User, UserProfile, InventoryItem, RecipeHistory)
    database.py             # SessionLocal engine
    requirements.txt
    .env.example            # suggested env layout (not committed with secrets)
  frontend/
    public/logo.png         # favicon/logo
    src/api/axios.js        # axios instance, baseURL from VITE_API_BASE_URL
    src/pages/              # Dashboard, RecipeGenerator, Profile, History, Login, Signup
    src/components/         # Layout, shared UI
    index.html              # head, favicon, title
    package.json
```

---

## Data Model (backend/models.py)

- User: id, username, email, hashed_password, created_at
- UserProfile: dietary_restrictions[], allergies[], favorite_cuisines[]
- InventoryItem: item_name, quantity, unit, expiry_date?, category, user_id, created_at
- RecipeHistory: recipe_json (generated), user_query, servings, feedback_score, is_cooked, created_at, user_id

---

## API Surface (key routes)

Auth
- `POST /auth/register` → {access_token, token_type}
- `POST /auth/token` → {access_token, token_type}

User profile
- `GET /users/profile` → username, email, dietary_restrictions, allergies, favorite_cuisines
- `PUT /users/profile` → update lists

Inventory
- `GET /inventory/` → list items (auth required)
- `POST /inventory/` → create item
- `PUT /inventory/{id}` → update item
- `DELETE /inventory/{id}` → delete item
- `POST /inventory/upload` → upload receipt (multipart), forwards to external OCR, returns detected items
- `POST /inventory/confirm_upload` → bulk insert confirmed OCR items

Recipes
- `POST /recipes/generate` → calls external recipe API (LLM), saves history, returns recipe payload
- `POST /recipes/{id}/cooked` → deducts inventory using smart_inventory parsing/conversion
- `POST /recipes/{id}/feedback` → save feedback score
- `GET /recipes/history` → newest-first recipe history
- `POST /recipes/video` → mock video URL by default; when `VIDEO_GEN_ENABLED` and Veo key present, attempts live video gen

---

## Smart Inventory Logic (utils/smart_inventory.py)

- Parsing: regex to extract qty/unit/name (handles decimals and fractions, prefix and parenthetical patterns).
- Unit normalization: maps plurals/variants to canonical units (lb/kg/g/oz, cup/tbsp/tsp/ml/l, pcs, can, bunch, head, clove).
- Unit conversion: weight and volume conversions; fallback to count when incompatible units.
- Fuzzy matching: similarity + token overlap to match recipe ingredient names to inventory items.
- Deduction: when cooked, attempts conversion and multiplies by servings; falls back to simple count when units incompatible.

---

## External Integrations

- Recipe generation: external API at Cloud Run (see `model_service.py`) returning JSON; robust parsing on frontend/backend to handle raw text or JSON.
- OCR: external OCR endpoint; response normalized, user confirms before insert.
- Video (optional): `/recipes/video` returns mock URL unless `VIDEO_GEN_ENABLED=true` and `VIDEO_GEN_API_KEY` set; uses google-genai client when enabled.

---

## Environment Variables

Backend (required unless noted)
- `DATABASE_URL` (Postgres/Neon) — required
- `SECRET_KEY` — required (JWT signing)
- `FRONTEND_ORIGIN` — optional; add prod frontend origin to CORS (localhost defaults always allowed)
- `VIDEO_GEN_ENABLED` — optional, default false
- `VIDEO_GEN_API_KEY`, `VIDEO_GEN_MODEL`, `VIDEO_GEN_TIMEOUT`, `VIDEO_GEN_POLL_SECONDS` — optional, for live video gen
- (If your recipe/OCR endpoints need keys, set them here; current endpoints are open)

Frontend
- `VITE_API_BASE_URL` — required in prod (backend URL)

---

## Local Development

Backend

```bash
cd model_deployment/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./pantry.db   # for local only; use Postgres in prod
export SECRET_KEY=devsecret
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend

```bash
cd model_deployment/frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

Smoke checks (manual)
- Register/login, confirm token stored and profile fetch works.
- Inventory CRUD.
- Recipe generate returns JSON; history shows entries.
- Mark cooked deducts inventory (watch quantities drop, with fallback when units mismatch).
- OCR upload returns detected items; confirm upload inserts items.
- Video button returns mock video preview (unless live enabled).

---

## Deployment (Render reference)

Backend (Web Service)
- Root: `model_deployment/backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env: `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_ORIGIN=https://<frontend>`, `VIDEO_GEN_ENABLED=false` (keep off unless using Veo)
- Python: set `PYTHON_VERSION=3.11.9`

Frontend (Static Site)
- Root: `model_deployment/frontend`
- Build: `npm install && npm run build`
- Publish dir: `dist`
- Env: `VITE_API_BASE_URL=https://<backend>`

Branch selection: Render lets you pick a branch per service; set it in service settings. Redeploy after env/branch changes.

---

## UX Walkthrough (frontend)

- Login/Signup pages: JWT auth flow.
- Dashboard: inventory grid with edit/delete, low-stock flags, OCR upload modal with confirm-and-edit flow.
- RecipeGenerator: servings selector, prompt input, animated loading, warning banners for missing inventory, parsed steps, feedback buttons, cooked action (inventory deduction), optional video preview widget (minimal copy).
- History: filter by liked/disliked/neutral, shows user query, timestamps, cooked badge, feedback status.
- Profile: update dietary restrictions, allergies, favorite cuisines (feeds backend preferences).

### UI Flow (high level)

```mermaid
flowchart TD
    L[Login or Signup] --> D[Dashboard]
    D -->|Add Edit Delete| Inventory[Inventory CRUD]
    D -->|Upload receipt| OCRFlow[OCR Modal Confirm Items Save]
    D --> R[Recipe Generator]
    R -->|Generate| RecResp[Show Recipe Warnings Steps]
    RecResp -->|Feedback| FB[Save Feedback]
    RecResp -->|Cooked| Cooked[Deduct Inventory]
    R -->|Video optional| Video[Mock or Live Video Preview]
    D --> H[History View filters]
    L --> P[Profile diet allergies cuisines]
    P --> R
```

---

## Operational Notes & Troubleshooting

- CORS: set `FRONTEND_ORIGIN` on backend; localhost ports (5173, 3000) always allowed.
- Auth: JWT signed with SECRET_KEY; ensure strong value in prod.
- DB: Do not use SQLite in prod; Postgres/Neon only. Ensure `DATABASE_URL` set before start.
- Video: Mock by default; enable only when Veo creds are provided. Fallback to mock on errors to avoid UX breaks.
- OCR: External dependency; if down, upload returns error payload without crashing UI.
- External recipe API: If it times out, backend saves a raw_text error in history; frontend handles gracefully.

---

## Future Extensions (handoff hints)

- Swap model_service to internal model (HF/PEFT) if running locally; keep signature.
- Add rate limiting / request logging middleware.
- Add migrations (Alembic) for schema evolution; currently relies on SQLAlchemy create_all.
- Promote video to first-class (progress polling endpoint, status persistence) if needed.

---

## License

MIT (see repo root).
