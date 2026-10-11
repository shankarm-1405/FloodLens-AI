"""
FloodLens AI - FastAPI Application Server
Multimodal AI Hackathon 2026: Track B (Mapping Flood Damage from Space)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router as base_router
from app.api.satellite import router as satellite_router
from app.api.flood import router as flood_router
from app.api.infrastructure import router as infrastructure_router
from app.api.connectivity import router as connectivity_router
from app.api.report import router as report_router

app = FastAPI(
    title="FloodLens AI API",
    description="Operational SAR & Optical Earth Observation API for Rapid Flood Mapping, Infrastructure Exposure, and Settlement Road Disconnection Modeling.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(base_router)
app.include_router(satellite_router)
app.include_router(flood_router)
app.include_router(infrastructure_router)
app.include_router(connectivity_router)
app.include_router(report_router)


@app.get("/")
def root():
    return {
        "project": "FloodLens AI",
        "description": "Satellite Multimodal Flood Damage Assessment Engine",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/api/health",
        "mode": "DEMO_FIXTURE_MODE" if settings.DEMO_MODE else "REAL_COPERNICUS_DATA_MODE"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
