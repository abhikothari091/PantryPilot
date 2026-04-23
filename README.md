# PantryPilot

AI-powered recipe generation from your pantry inventory.

## Overview

PantryPilot generates personalized recipes based on the ingredients you have on hand. It respects dietary restrictions, allergies, and cuisine preferences while minimizing food waste.

## Features

- **Inventory-based recipe generation** – generates recipes using ingredients you already have
- **Dietary restriction enforcement** – hard blocklists prevent forbidden ingredients from appearing in any prompt
- **Allergy-aware suggestions** – life-threatening allergens are explicitly excluded
- **Cuisine preference support** – favourite cuisines are factored into generation
- **Recipe history & feedback** – like/dislike recipes to improve future suggestions
- **DPO preference collection** – every 7th generation produces two variants for human preference labelling

## Dietary Constraint Negative Prompt Injection

When a user has active dietary flags, the backend injects structured negative constraint strings directly into every recipe generation prompt. This is handled by `build_negative_constraint_string` in `model_deployment/backend/model_service.py`.

### How it works

1. The user's `dietary_restrictions` list is read from their profile (e.g. `["gluten-free", "vegan"]`).
2. For each active flag, its full blocklist is looked up in `DIETARY_BLOCKLISTS`.
3. A line of the form `Do not include: <comma-separated ingredients>` is assembled per flag.
4. All lines are joined and appended to `strict_restrictions`, which is prepended to the prompt under the `⚠️ MANDATORY RESTRICTIONS` header.

### Per-flag blocklists

| Flag | Key excluded ingredients (examples) |
|---|---|
| `gluten-free` | wheat flour, all-purpose flour, soy sauce, barley, rye, bread, pasta, panko, breadcrumbs, malt |
| `vegan` | honey, gelatin, gelatine, eggs, milk, butter, cream, cheese, beef stock, chicken stock, fish sauce, anchovy |
| `dairy-free` | butter, cream, cheese, milk, yogurt, cheddar, mozzarella, parmesan, ghee, buttermilk, whey, casein |
| `nut-free` | peanuts, peanut butter, almonds, almond flour, walnuts, cashews, pecans, pistachios, macadamia nuts, brazil nuts, hazelnuts, pine nuts, tree nuts |

### Example output

For a user with flags `["gluten-free", "dairy-free"]`, the injected text looks like:

```
Do not include: wheat flour, all-purpose flour, bread flour, barley, rye, soy sauce, wheat, bread, pasta, noodles, couscous, semolina, spelt, farro, bulgur, wheat germ, wheat bran, malt, beer, ale, crackers, croutons, panko, breadcrumbs
Do not include: butter, cream, cheese, milk, yogurt, cheddar, mozzarella, parmesan, brie, gouda, feta, ricotta, cream cheese, sour cream, half-and-half, heavy cream, whipping cream, condensed milk, evaporated milk, ghee, whey, casein, lactose, buttermilk
```

### API reference

```python
from model_service import build_negative_constraint_string, DIETARY_BLOCKLISTS

# Build constraint string for active flags
constraint = build_negative_constraint_string(["vegan", "nut-free"])
# Returns two lines joined by newline:
# "Do not include: honey, gelatin, ...
# Do not include: peanuts, almonds, ..."
```

## Project structure

```
.
├── model_deployment/
│   └── backend/
│       ├── model_service.py        # ModelService, DIETARY_BLOCKLISTS, build_negative_constraint_string
│       ├── models.py               # SQLAlchemy ORM models
│       ├── routers/
│       │   ├── recipes.py          # Recipe generation, history, feedback endpoints
│       │   └── inventory.py        # Inventory management endpoints
│       └── services/
├── model_development/
│   └── training_pipeline/
│       └── 03_validation/
│           └── validate_dietary_constraints.py
└── tests/
    └── backend/
        ├── test_recipes.py
        └── test_model_service.py   # Unit tests for build_negative_constraint_string
```

## Running tests

```bash
# All tests
pytest tests/

# Only API tests
pytest tests/ -m api

# Model service unit tests (dietary constraints)
pytest tests/backend/test_model_service.py -v
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_SERVICE_TIMEOUT` | `60` | Timeout in seconds for external LLM API calls |
| `VIDEO_GEN_ENABLED` | `false` | Enable video generation feature |
| `VIDEO_GEN_ALLOW_LIVE` | `false` | Allow live (non-fallback) video generation |
| `VIDEO_GEN_API_KEY` | – | Google GenAI API key for video generation |
| `VIDEO_GEN_TIMEOUT` | `180` | Timeout for video generation polling |
| `VIDEO_GEN_POLL_SECONDS` | `10` | Poll interval for video generation status |

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend
cd model_deployment/backend
uvicorn main:app --reload
```
