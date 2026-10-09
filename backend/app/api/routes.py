"""
Primary API routes for FloodLens AI: Health, Configuration, Version, and Provenance.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api", tags=["System & Provenance"])

REQUIRED_ATTRIBUTIONS = [
    "Contains modified Copernicus Sentinel data 2026.",
    "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.",
    "© OpenStreetMap contributors."
]


@router.get("/health", response_model=Dict[str, Any])
def get_health() -> Dict[str, Any]:
    """
    Health check endpoint reporting system status, operational mode,
    geospatial library availability, and server timestamp.
    """
    # Verify core geospatial libraries
    geo_status = {}
    try:
        import rasterio
        geo_status["rasterio"] = {"available": True, "version": rasterio.__version__}
    except Exception as e:
        geo_status["rasterio"] = {"available": False, "error": str(e)}

    try:
        import shapely
        geo_status["shapely"] = {"available": True, "version": shapely.__version__}
    except Exception as e:
        geo_status["shapely"] = {"available": False, "error": str(e)}

    try:
        import geopandas
        geo_status["geopandas"] = {"available": True, "version": geopandas.__version__}
    except Exception as e:
        geo_status["geopandas"] = {"available": False, "error": str(e)}

    try:
        import networkx
        geo_status["networkx"] = {"available": True, "version": networkx.__version__}
    except Exception as e:
        geo_status["networkx"] = {"available": False, "error": str(e)}

    all_geo_healthy = all(item.get("available", False) for item in geo_status.values())

    return {
        "status": "healthy" if all_geo_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "FloodLens AI Backend",
        "demo_mode": settings.DEMO_MODE,
        "geospatial_stack": geo_status,
        "study_case": {
            "region": "Trishuli Corridor, Nepal",
            "default_bbox": settings.DEFAULT_AOI_BBOX,
            "default_event_date": settings.DEFAULT_EVENT_DATE,
            "osm_snapshot_date": settings.OSM_SNAPSHOT_DATE,
        }
    }


@router.get("/version", response_model=Dict[str, Any])
def get_version() -> Dict[str, Any]:
    """
    Version, challenge metadata, and official attribution notices.
    """
    return {
        "name": "FloodLens AI",
        "version": "1.0.0",
        "hackathon": "Multimodal AI Hackathon 2026",
        "track": "Track B: Mapping Flood Damage from Space",
        "attributions": REQUIRED_ATTRIBUTIONS,
        "disclaimer": "Educational and research prototype for disaster risk assessment. Not for life-critical tactical operations without verified in-situ validation."
    }


@router.get("/config-status", response_model=Dict[str, Any])
def get_config_status() -> Dict[str, Any]:
    """
    Returns public non-secret configuration statuses (credentials are masked).
    """
    return {
        "demo_mode": settings.DEMO_MODE,
        "cdse_configured": settings.has_cdse_credentials,
        "cdse_auth_type": "OAuth2 Client Credentials" if (settings.CDSE_CLIENT_ID and settings.CDSE_CLIENT_SECRET) else ("Username/Password" if settings.CDSE_USERNAME else "None"),
        "osm_snapshot_date": settings.OSM_SNAPSHOT_DATE,
        "osm_overpass_endpoint": settings.OSM_OVERPASS_ENDPOINT,
        "llm_grounding_configured": settings.has_llm_key,
        "llm_provider": settings.LLM_PROVIDER if settings.has_llm_key else "deterministic_grounded_fallback",
        "default_aoi_bbox": settings.DEFAULT_AOI_BBOX,
        "default_event_date": settings.DEFAULT_EVENT_DATE,
    }


@router.get("/attribution", response_model=Dict[str, Any])
def get_attribution() -> Dict[str, Any]:
    """
    Returns legal attribution statements for European Union / ESA Copernicus and OpenStreetMap.
    """
    return {
        "required_statements": REQUIRED_ATTRIBUTIONS,
        "details": [
            {
                "data_source": "Copernicus Sentinel-1 SAR & Sentinel-2 MSI",
                "statement": "Contains modified Copernicus Sentinel data 2026.",
                "license": "Copernicus Open Access / Legal notice on the use of Copernicus Sentinel Data and Service Information."
            },
            {
                "data_source": "Copernicus WorldDEM-30",
                "statement": "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.",
                "license": "Copernicus WorldDEM License Agreement"
            },
            {
                "data_source": "OpenStreetMap",
                "statement": "© OpenStreetMap contributors.",
                "license": "Open Data Commons Open Database License (ODbL) 1.0"
            }
        ]
    }
