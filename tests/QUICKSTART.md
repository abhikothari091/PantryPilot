# Quick Start - Running Tests

## Backend Tests
```bash
# Install dependencies (first time only)
pip install -r tests/requirements.txt

# Run all tests
pytest tests/backend/ -v

# Run with coverage
pytest tests/backend/ --cov=model_deployment/backend --cov-report=term

# Run specific category
pytest tests/backend/ -m auth  # Auth tests only
pytest tests/backend/ -m unit  # Unit tests only
```

## Frontend Tests
```bash
# Install dependencies (first time only)
cd model_deployment/frontend
npm install

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm test -- --watch
```

## View Coverage Reports
```bash
# Backend
open tests/coverage/backend/index.html

# Frontend
open model_deployment/frontend/coverage/index.html
```

## CI/CD
Tests run automatically on:
- Push to `main` or `dev` branches
- Pull requests

Check results at: GitHub Actions → Tests workflow
