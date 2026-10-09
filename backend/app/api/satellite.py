"""
Satellite Data Discovery and Retrieval API Router
Handles Sentinel-1 SAR and Sentinel-2 optical catalog queries,
orbit/geometry compatibility analysis, and retrieval readiness.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.core.copernicus import (
    copernicus_client,
    InvalidCoordinatesError,
    InvalidDateError
)
from app.fixtures.demo_data import (
    DEMO_SENTINEL1_ACQUISITIONS,
    DEMO_SENTINEL2_ACQUISITIONS,
    DEMO_DISCLAIMER
)

router = APIRouter(prefix="/api/satellite", tags=["Satellite Earth Observation"])


class SearchRequest(BaseModel):
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Geographic bounding box [min_lon, min_lat, max_lon, max_lat] in EPSG:4326"
    )
    event_date: Optional[str] = Field(
        default=None,
        description="Flood event reference anchor date formatted as YYYY-MM-DD"
    )
    window_days: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Temporal search window (days) before and after the event date"
    )
    include_optical: bool = Field(
        default=True,
        description="Search for Sentinel-2 optical acquisitions to evaluate cloud coverage"
    )
    force_live: bool = Field(
        default=False,
        description="Forces live query to Copernicus Data Space Ecosystem even if DEMO_MODE is true"
    )


@router.post("/search")
def search_satellite_acquisitions(req: SearchRequest) -> Dict[str, Any]:
    """
    Search for pre- and post-event Sentinel-1 radar scenes and Sentinel-2 optical scenes.
    Performs viewing geometry compatibility evaluation (orbit direction and relative track matching).
    """
    target_bbox = req.bbox if req.bbox is not None else settings.DEFAULT_AOI_BBOX
    target_date = req.event_date if req.event_date is not None else settings.DEFAULT_EVENT_DATE

    # Validate inputs
    try:
        copernicus_client.validate_aoi_bbox(target_bbox)
        copernicus_client.validate_event_date(target_date)
    except (InvalidCoordinatesError, InvalidDateError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check operational mode: If DEMO_MODE is active and user didn't force live search, return labeled demo fixture
    if settings.DEMO_MODE and not req.force_live:
        # Build demo compatible pairs
        pre_demo = [a for a in DEMO_SENTINEL1_ACQUISITIONS if a["timing_relation"] == "PRE_EVENT"]
        post_demo = [a for a in DEMO_SENTINEL1_ACQUISITIONS if a["timing_relation"] == "POST_EVENT"]

        compatible_pairs = [
            {
                "pre_event_scene": pre_demo[0],
                "post_event_scene": post_demo[0],
                "compatibility_score": 0.95,
                "compatibility_level": "OPTIMAL",
                "explanation": "Demonstration Optimal Pair: Matching Descending pass and identical track 121.",
                "detailed_criteria": [
                    "Matching orbit direction: DESCENDING",
                    "Identical track (Relative Orbit 121)",
                    "Identical polarization: VV&VH"
                ],
                "temporal_separation_days": 8.0,
                "label": DEMO_DISCLAIMER
            }
        ]

        return {
            "mode": "DEMONSTRATION_MODE",
            "is_demo_fixture": True,
            "disclaimer": DEMO_DISCLAIMER,
            "query_parameters": {
                "bbox": target_bbox,
                "event_date": target_date,
                "window_days": req.window_days
            },
            "sentinel1": {
                "total_found": len(DEMO_SENTINEL1_ACQUISITIONS),
                "pre_event_acquisitions": pre_demo,
                "post_event_acquisitions": post_demo,
                "compatible_pairs": compatible_pairs,
                "best_compatible_pair": compatible_pairs[0]
            },
            "sentinel2": {
                "total_found": len(DEMO_SENTINEL2_ACQUISITIONS),
                "acquisitions": DEMO_SENTINEL2_ACQUISITIONS if req.include_optical else []
            },
            "provenance": {
                "source": "FloodLens AI Bundled Demonstration Fixture",
                "notice": "DEMONSTRATION DATA — NOT REAL FLOOD ANALYSIS",
                "legal_attribution": "Contains modified Copernicus Sentinel data 2026."
            }
        }

    # Execute REAL live search against Copernicus Data Space Ecosystem (CDSE)
    s1_results = copernicus_client.search_sentinel1_acquisitions(
        bbox=target_bbox,
        event_date_str=target_date,
        window_days=req.window_days
    )

    s2_results = {}
    if req.include_optical:
        s2_results = copernicus_client.search_sentinel2_acquisitions(
            bbox=target_bbox,
            event_date_str=target_date,
            window_days=req.window_days
        )

    return {
        "mode": "REAL_DATA_MODE",
        "is_demo_fixture": False,
        "query_parameters": {
            "bbox": target_bbox,
            "event_date": target_date,
            "window_days": req.window_days
        },
        "sentinel1": s1_results,
        "sentinel2": s2_results,
        "provenance": {
            "source": "Copernicus Data Space Ecosystem (CDSE) Live OData Catalogue",
            "catalogue_endpoint": settings.CDSE_CATALOGUE_URL,
            "legal_attribution": "Contains modified Copernicus Sentinel data 2026."
        }
    }


@router.get("/credentials-status")
def get_credentials_status() -> Dict[str, Any]:
    """
    Checks Copernicus CDSE authentication status and provides registration guidance.
    """
    has_creds = settings.has_cdse_credentials
    token = copernicus_client.get_auth_token() if has_creds else None

    return {
        "configured": has_creds,
        "token_active": bool(token),
        "auth_method": (
            "OAuth2 Client Credentials" if (settings.CDSE_CLIENT_ID and settings.CDSE_CLIENT_SECRET)
            else ("Username / Password" if settings.CDSE_USERNAME else "None")
        ),
        "guidance": {
            "registration_portal": "https://dataspace.copernicus.eu/",
            "instructions": (
                "To enable raw product downloads from CDSE, register a free account at "
                "https://dataspace.copernicus.eu/ and add CDSE_USERNAME and CDSE_PASSWORD "
                "to your .env configuration file."
            )
        }
    }


@router.post("/download-check")
def check_download_readiness(product_id: str = Query(..., description="CDSE Product UUID")) -> Dict[str, Any]:
    """
    Validates download authorization and file status for a specific product.
    Does not falsely state that data were downloaded unless completion is verified.
    """
    return copernicus_client.prepare_download(product_id)
