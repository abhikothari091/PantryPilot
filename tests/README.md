# PantryPilot Test Suite

Comprehensive test suite for PantryPilot covering backend (FastAPI) and frontend (React) with 80%+ coverage target.

## 🏗️ Structure

```
tests/
├── backend/                    # pytest tests for FastAPI backend
│   ├── conftest.py            # Fixtures, mocks, test database
│   ├── test_auth.py           # Authentication endpoints
│   ├── test_inventory.py      # Inventory CRUD + OCR
│   ├── test_recipes.py        # Recipe generation, cooked, warmup
│   ├── test_gluten_free_safety.py  # Gluten-free blocklist enforcement (20+ cases)
│   ├── test_users.py          # User profile management
│   ├── test_models.py         # SQLAlchemy models
│   └── test_smart_inventory.py # Unit conversion & fuzzy matching
├── frontend/                   # Vitest tests for React frontend
│   ├── setup.ts               # Test environment setup
│   ├── AuthContext.test.jsx   # Authentication context
│   ├── Dashboard.test.jsx     # Inventory dashboard
│   ├── RecipeGenerator.test.jsx # Recipe generator UI
│   └── axios.test.js          # API client & interceptors
└── coverage/                   # Generated coverage reports
```

## 🚀 Running Tests

### All Tests
```bash
# From repository root
pytest tests/backend/ -v
```

### Gluten-Free Safety Suite Only
```bash
pytest tests/backend/test_gluten_free_safety.py -v
```

### With coverage report
```bash
pytest tests/backend/ --cov=model_deployment/backend --cov-report=term-missing
```

### Skip slow tests
```bash
pytest tests/backend/ -m "not slow"
```

---

## 🛡️ Gluten-Free Safety Test Suite

`tests/backend/test_gluten_free_safety.py` — 20+ integration tests that fire
recipe generation requests against the FastAPI backend (LLM mocked) and assert
that blocklist enforcement, retry logic, and logging all behave correctly.

### Test categories

| Category | Count | What it checks |
|---|---|---|
| Clean recipes | 8 | Safe GF responses accepted, no blocklist hits in response |
| Single-hit violations | 7 | One blocklisted ingredient triggers retry; clean retry accepted |
| Multi-hit violations | 3 | Multiple blocklisted ingredients trigger retry; clean retry accepted |
| Retry exhaustion | 2 | Both attempts violate; response must not surface the ingredient |
| Retry call counts | 2 | Exactly 2 LLM calls on violation, 1 on clean |
| Logging | 3 | Structured log records emitted during GF generation events |

### Running locally

```bash
# From repo root
pytest tests/backend/test_gluten_free_safety.py -v

# Run a single test
pytest tests/backend/test_gluten_free_safety.py::test_gf_single_violation_soy_sauce_retry_succeeds -v

# Run only violation tests
pytest tests/backend/test_gluten_free_safety.py -k "violation" -v
```

### Adding a new blocklist test case

1. **Update the blocklist constant** in `tests/backend/conftest.py`:
   ```python
   GLUTEN_BLOCKLIST = [
       ...
       "your_new_ingredient",   # add here
   ]
   ```
   Keep this list in sync with the backend blocklist module
   (`model_deployment/backend/` — see Task 1 implementation).

2. **Add a clean recipe test** (if the ingredient has a safe GF alternative):
   ```python
   @pytest.mark.api
   def test_gf_clean_your_scenario(client, gluten_free_auth_headers, gluten_free_inventory):
       mock_service = Mock()
       mock_service.generate_recipe.return_value = make_clean_gf_recipe(
           name="My Safe Recipe",
           ingredients=["rice", "chicken", "safe_alternative"]
       )
       client.app.state.model_service = mock_service
       response = _post_recipe(client, gluten_free_auth_headers, "my dish")
       assert response.status_code == 200
       _assert_no_blocklist_hit(response)
   ```

3. **Add a violation test** for the new ingredient:
   ```python
   @pytest.mark.api
   def test_gf_single_violation_your_ingredient_retry_succeeds(
       client, gluten_free_auth_headers, gluten_free_inventory
   ):
       mock_service = Mock()
       mock_service.generate_recipe.side_effect = [
           make_violation_gf_recipe(["your_new_ingredient"]),
           make_clean_gf_recipe(name="Safe Alternative"),
       ]
       client.app.state.model_service = mock_service
       response = _post_recipe(client, gluten_free_auth_headers, "dish that uses it")
       assert response.status_code == 200
       _assert_no_blocklist_hit(response)
   ```

4. Run the suite to confirm the new tests pass:
   ```bash
   pytest tests/backend/test_gluten_free_safety.py -v
   ```

### Key fixtures (defined in `conftest.py`)

| Fixture | Description |
|---|---|
| `gluten_free_user` | User with `dietary_restrictions=["gluten-free"]` |
| `gluten_free_auth_headers` | Bearer token headers for the GF user |
| `gluten_free_inventory` | Inventory stocked with safe GF ingredients |
| `GLUTEN_BLOCKLIST` | Canonical list of hidden-gluten ingredients to test against |
| `make_clean_gf_recipe()` | Helper that builds a violation-free recipe JSON string |
| `make_violation_gf_recipe([...])` | Helper that builds a recipe JSON string containing the given blocklisted ingredients |

### How mocking works

All LLM calls are eliminated by injecting a `unittest.mock.Mock` directly into
`client.app.state.model_service` — the same pattern used throughout the rest of
the backend test suite. `side_effect` is used for retry scenarios so the first
call returns a violation and the second returns a clean recipe:

```python
mock_service.generate_recipe.side_effect = [
    make_violation_gf_recipe(["soy sauce"]),  # first call — triggers retry
    make_clean_gf_recipe(),                   # second call — passes validation
]
client.app.state.model_service = mock_service
```
