from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine
from models import Base
from routers import auth, inventory, recipes, users
from model_service import get_model_service

# Create tables
Base.metadata.create_all(bind=engine)

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(recipes.router)
app.include_router(users.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "PantryPilot API is running"}
