from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    analysis,
    auth,
    cases,
    evidence,
    forensic_analysis,
    fraud,
    location_analysis,
)

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def application_lifespan(
    app: FastAPI,
):
    """
    Runs when FastAPI starts.

    It creates database tables that do not already exist.
    """

    Base.metadata.create_all(
        bind=engine
    )

    yield


app = FastAPI(
    title=settings.app_name,
    version="1.2.0",
    description=(
        "Forensic CDR ingestion, normalization, "
        "analysis and explainable behavioural pattern "
        "detection backend."
    ),
    lifespan=application_lifespan,
)


# =========================================================
# Authentication routes
# =========================================================

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"],
)


# =========================================================
# Case routes
# =========================================================

app.include_router(
    cases.router,
    prefix="/api/cases",
    tags=["Cases"],
)


# =========================================================
# Evidence routes
# =========================================================

app.include_router(
    evidence.router,
    prefix="/api",
    tags=["Evidence"],
)


# =========================================================
# General analysis routes
# =========================================================

app.include_router(
    analysis.router,
    prefix="/api",
    tags=["Analysis"],
)


# =========================================================
# Location analysis routes
# =========================================================

app.include_router(
    location_analysis.router,
    prefix="/api",
    tags=["Location Analysis"],
)


# =========================================================
# Forensic analysis routes
# =========================================================

app.include_router(
    forensic_analysis.router,
    prefix="/api",
    tags=["Forensic Analysis"],
)


# =========================================================
# Pattern analysis routes
# =========================================================

app.include_router(
    fraud.router,
    prefix="/api",
    tags=["Pattern Analysis"],
)


# =========================================================
# CORS configuration
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# System routes
# =========================================================

@app.get(
    "/",
    tags=["System"],
)
def root():
    return {
        "application": settings.app_name,
        "message": (
            "CDR Analyzer API is running."
        ),
        "version": "1.2.0",
        "swagger_documentation": "/docs",
    }


@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    return {
        "status": "healthy",
        "pattern_analysis": "enabled",
    }