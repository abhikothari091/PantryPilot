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
python -m pytest tests/backend/ --cov=model_deployment/backend --cov-report=html
cd model_deployment/frontend && npm test
```

### Backend Only
```bash
pytest tests/backend/ -v
pytest tests/backend/ --cov=model_deployment/backend --cov-report=term
```

### Frontend Only
```bash
cd model_deployment/frontend
npm test                    # Run tests
npm run test:coverage      # With coverage
```

### Watch Mode
```bash
# Backend (pytest-watch)
ptw tests/backend/

# Frontend (Vitest watch)
cd model_deployment/frontend && npm test -- --watch
```

## 📊 Coverage Reports

Coverage reports are generated in:
- **Backend**: `tests/coverage/backend/`
- **Frontend**: `model_deployment/frontend/coverage/`

View HTML reports:
```bash
# Backend
open tests/coverage/backend/index.html

# Frontend
open model_deployment/frontend/coverage/index.html
```

## 🧪 Test Categories

### Backend Tests
- **Unit Tests**: Smart inventory functions, utilities
- **Integration Tests**: API endpoints with mocked database
- **Authentication**: Register, login, JWT validation
- **CRUD**: Inventory, recipes, user profiles
- **External APIs**: Mocked LLM, OCR, video generation

### Frontend Tests
- **Component Tests**: React components in isolation
- **Hook Tests**: Custom hooks (useAuth)
- **Integration Tests**: API calls with mocked axios
- **UI Interactions**: User flows, form submissions

## ✅ Coverage Goals

Target: **80%+ overall coverage**

- Backend: 85%+ (critical business logic)
- Frontend: 75%+ (UI components)

## 🔧 CI/CD Integration

Tests run automatically on:
- Every push to `main`
- All pull requests
- Pre-deployment checks

See `.github/workflows/test.yml` for CI configuration.

## 📝 Writing New Tests

### Backend (pytest)
```python
def test_example(client, auth_headers):
    response = client.post("/api/endpoint", 
                          json={"data": "value"},
                          headers=auth_headers)
    assert response.status_code == 200
```

### Frontend (Vitest + React Testing Library)
```jsx
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

test('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

## 🐛 Debugging Tests

```bash
# Backend: Run specific test
pytest tests/backend/test_auth.py::test_login -v

# Backend: Print debug output
pytest tests/backend/test_auth.py -s

# Frontend: Debug specific test
cd model_deployment/frontend && npm test -- test_name
```

## 📦 Dependencies

### Backend
- pytest
- pytest-cov
- pytest-mock
- httpx (FastAPI test client)

### Frontend
- vitest
- @testing-library/react
- @testing-library/jest-dom
- happy-dom (jsdom alternative)
