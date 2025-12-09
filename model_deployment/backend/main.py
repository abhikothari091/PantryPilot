from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from database import engine
from models import Base
from routers import auth, inventory, recipes, users, admin, training
from model_service import get_model_service

# Allow importing shared observability helpers from the parent folder
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from observability import (  # noqa: E402
    ObservabilityMiddleware,
    collect_health,
    configure_logging,
    metrics_response,
)

# Create tables
Base.metadata.create_all(bind=engine)

# Configure structured logging early
configure_logging(service_name="pantrypilot-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model
    print("🚀 Initializing PantryPilot Backend...")
    try:
        app.state.model_service = get_model_service()
        print("✅ Model Service Ready")
    except Exception as e:
        print(f"⚠️ Failed to load model service: {e}")
        app.state.model_service = None
    
    yield
    
    # Shutdown: Cleanup
    if app.state.model_service:
        app.state.model_service.cleanup()
    print("👋 Shutting down...")

app = FastAPI(title="PantryPilot API", lifespan=lifespan)

# CORS
frontend_origin = os.getenv("FRONTEND_ORIGIN")
default_origins = ["http://localhost:5173", "http://localhost:3000"]
allow_origins = [frontend_origin] + default_origins if frontend_origin else default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins, # Vite default ports + optional FRONTEND_ORIGIN
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability (request logs, metrics, request_id propagation)
app.add_middleware(ObservabilityMiddleware, service_name="pantrypilot-backend")

# Include Routers
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(recipes.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(training.router)

@app.get("/healthz")
def healthcheck():
    """
    Lightweight liveness/readiness probe with DB connectivity check.
    Never raises; marks status=degraded if DB is unreachable.
    """
    return collect_health(engine)


@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    return metrics_response()

@app.get("/")
def root():
    return {"status": "ok", "message": "PantryPilot API is running"}
