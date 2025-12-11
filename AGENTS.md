# Repository Guidelines

## Project Structure & Module Organization
- `data_pipeline/` – Airflow DAG plus ingestion, validation, transform, and alert scripts; DVC tracks `data/{raw,processed,alerts}` snapshots.
- `model_development/` – recipe LLM evaluation, reward modeling, and training pipeline snapshots; keep adapters/checkpoints under `model_development/models/`.
- `model_deployment/` – FastAPI service (routers/services under `backend/`) and the Vite/Tailwind frontend (`frontend/src/`).
- Tests live in `tests/backend/` (pytest mirroring API routes) and alongside React components in `model_deployment/frontend/src/**/*.test.*`.

## Build, Test, and Development Commands
```bash
python data_pipeline/scripts/ingest_neon.py
python data_pipeline/scripts/validate_data.py
python data_pipeline/scripts/transform_data.py
python data_pipeline/scripts/update_anomalies.py
dvc pull raw.dvc processed.dvc alerts.dvc

uvicorn model_deployment.backend.main:app --reload
cd model_deployment/frontend && npm install && npm run dev

python -m pytest tests/backend --cov=model_deployment/backend --cov-report=term
cd model_deployment/frontend && npm test
```
Use `airflow dags test pantrypilot_data_pipeline <date>` for DAG dry-runs, `dvc status` before pushing data changes, and `npm run build` when preparing production bundles.

## Coding Style & Naming Conventions
- Python (3.11) follows PEP8 with 4-space indents, type-hinted dataclasses, and `snake_case` modules; FastAPI routers should stay thin and delegate to `services/` helpers.
- JavaScript/TypeScript uses ES modules, PascalCase React components, and `camelCase` hooks/utilities; run `npm run lint` (ESLint + Vite) and keep Tailwind classes grouped by layout → color → effects to avoid churn.
- Configuration flows through `.env` files loaded via `dotenv`; reference variable names in docs but never commit real secrets (NeonDB URLs, HF tokens, GCS JSON).

## Testing Guidelines
- Backend pytest fixtures live in `tests/backend/conftest.py`; name files after the feature (`test_inventory.py`, `test_recipes.py`) and target ≥85% coverage using `--cov-report=html`.
- Frontend Vitest specs mirror component folders and rely on Testing Library (`screen.getByRole`).
- For pipeline additions, include at least one unit test under `data_pipeline/tests/` and mention recent Airflow smoke runs in the PR.

## Commit & Pull Request Guidelines
- Match the existing imperative, scope-first commit pattern (`Update Slack alert conditions`, `Hook training approval into retraining service`) and keep subject lines ≤72 characters.
- Every PR should summarize the change, link an issue, list the commands/tests you ran, and attach screenshots or sample payloads for UI/API updates. Mention any DVC artifacts touched so reviewers can sync them.

## Configuration & Security Tips
- Export `DATABASE_URL`, `GOOGLE_APPLICATION_CREDENTIALS`, and `HF_TOKEN` locally instead of hard-coding paths; scripts read them via `dotenv`.
- Use `gcloud auth application-default login` (or workload identity) for DVC pushes to GCS, rotate credentials before demos, and keep large weights or `.db` files out of Git history.
