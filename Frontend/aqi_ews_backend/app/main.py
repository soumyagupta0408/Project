"""
app/main.py
FastAPI application factory — AQI Sentinel backend.
"""
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import engine, Base

# Import all models so Alembic / Base.metadata can see them
from app.models import user, alert, aqi_reading  # noqa: F401

from app.api.routes import auth, aqi, users

settings = get_settings()

# ── Create tables (dev convenience; use Alembic in production) ────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AQI Sentinel API",
    description="Backend for the AQI Sentinel Streamlit dashboard — Indore, MP.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow Streamlit frontend) ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(aqi.router)
app.include_router(users.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "app": "AQI Sentinel"}

@app.get("/")
def home():
    return {"message": "API is working 🚀"}
