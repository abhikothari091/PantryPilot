# PantryPilot

AI-powered recipe generation from your pantry inventory.

## Overview

PantryPilot generates personalized recipes based on your available ingredients and dietary preferences. It uses an external LLM API to produce structured JSON recipes, enforce dietary restrictions, and track your cooking history.

## Features

- **Inventory-aware recipe generation** – recipes prioritise ingredients you already have.
- **Dietary restriction enforcement** – active flags are injected as explicit negative constraints into every generation prompt.
- **Recipe history & feedback** – like/dislike ratings stored per user.
- **A/B comparison mode** – every 7th generation returns two variants for preference collection (used for DPO fine-tuning).
- **Smart inventory deduction** – marking a recipe as cooked automatically reduces ingredient quantities.

## Dietary Constraint Blocklists

Each dietary flag maps to a hardcoded blocklist in `model_deployment/backend/model_service.py` (`DIETARY_BLOCKLISTS`). When a flag is active, its full blocklist is appended to the generation prompt as a structured negative constraint string:

```
Do not include: <comma-separated blocked ingredients>
```

Multiple active flags each produce their own line, concatenated with newlines.

### Supported flags and key blocked ingredients

| Flag | Key blocked ingredients |
|---|---|
| `gluten-free` | wheat flour, all-purpose flour, bread flour, barley, rye, **soy sauce**, wheat, bread, pasta, noodles, couscous, semolina, spelt, farro, bulgur, malt, beer, panko, breadcrumbs, … |
| `vegan` | **honey**, **gelatin** / gelatine, eggs, milk, butter, cream, cheese, yogurt, whey, casein, lard, beef stock, chicken stock, fish sauce, anchovy, worcestershire sauce, mayonnaise, ghee, … |
| `dairy-free` | **butter**, **cream**, **cheese**, milk, yogurt, cheddar, mozzarella, parmesan, brie, gouda, feta, ricotta, sour cream, heavy cream, condensed milk, ghee, whey, casein, buttermilk, … |
| `nut-free` | **peanuts**, peanut butter, peanut oil, **almonds**, almond flour, almond milk, **walnuts**, **cashews**, **pecans**, pistachios, macadamia nuts, brazil nuts, hazelnuts, pine nuts, tree nuts, nut butter, … |

### How it works

1. The router reads the user's `dietary_restrictions` from their profile.
2. `build_negative_constraint_string(dietary_flags)` in `model_service.py` iterates over each active flag, looks up its blocklist, and formats a `Do not include: …` line.
3. The resulting string is appended to `strict_restrictions`, which is prepended to the prompt sent to the external LLM API under the `⚠️ MANDATORY RESTRICTIONS` header.

### Helper function

```python
from model_service import build_negative_constraint_string

constraint = build_negative_constraint_string(["vegan", "gluten-free"])
# Returns:
# "Do not include: honey, gelatin, gelatine, eggs, ...
# Do not include: wheat flour, all-purpose flour, ..., soy sauce, ..."
```

## Project Structure

```
model_deployment/
  backend/
    model_service.py        # External API client + DIETARY_BLOCKLISTS + build_negative_constraint_string
    routers/
      recipes.py            # Recipe generation, history, feedback, comparison endpoints
    models.py               # SQLAlchemy ORM models
    dependencies.py         # FastAPI dependency helpers
tests/
  backend/
    test_recipes.py         # API + blocklist unit tests
model_development/
  training_pipeline/
    03_validation/
      validate_dietary_constraints.py  # Training-data dietary violation checker
```

## Running Tests

```bash
pytest tests/backend/test_recipes.py
```

The test suite includes dedicated unit tests for all four dietary flag combinations:

- `test_build_negative_constraint_gluten_free` – verifies soy sauce, barley, rye, wheat flour are present.
- `test_build_negative_constraint_vegan` – verifies honey and gelatin are present.
- `test_build_negative_constraint_dairy_free` – verifies butter, cream, and cheese are present.
- `test_build_negative_constraint_nut_free` – verifies peanuts, almonds, walnuts, cashews, and pecans are present.
- `test_build_negative_constraint_multiple_flags` – verifies each flag produces its own `Do not include:` line.
- `test_build_negative_constraint_no_flags` – verifies empty input returns an empty string.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_SERVICE_TIMEOUT` | `60` | HTTP timeout (seconds) for the external LLM API |
| `VIDEO_GEN_ENABLED` | `false` | Enable video generation feature |
| `VIDEO_GEN_ALLOW_LIVE` | `false` | Allow live (non-fallback) video generation |
| `VIDEO_GEN_API_KEY` | – | Google GenAI API key for video generation |
| `VIDEO_GEN_TIMEOUT` | `180` | Timeout for video generation polling |
| `VIDEO_GEN_POLL_SECONDS` | `10` | Polling interval for video generation |
