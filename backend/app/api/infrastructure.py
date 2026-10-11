"""
Infrastructure Exposure Analysis API Router
FloodLens AI - Phase 4: Historical OSM Exposure Assessment

Endpoints for triggering spatial exposure calculations between Sentinel-1 flood extents
and pre-event OpenStreetMap infrastructure, retrieving summary metrics, downloading GeoJSON,
and inspecting critical facility vulnerability.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings, OUTPUTS_DIR
from app.core.infrastructure import (
    infrastructure_engine,
    osm_client,
    validate_analysis_id,
    InfrastructureError,
    HistoricalSnapshotUnavailableError,
    MissingFloodAnalysisError,
    InvalidGeometryError,
    OSM_ATTRIBUTION
)

router = APIRouter(prefix="/api/infrastructure", tags=["Infrastructure Exposure Assessment"])


class InfrastructureAnalysisRequest(BaseModel):
    analysis_id: str = Field(
        ...,
        description="ID of a validated Phase 3 Sentinel-1 flood analysis"
    )
    osm_source: Optional[str] = Field(
        default="historical",
        description="Source of OSM data: 'historical' (2026-07-27 baseline) or 'current_preview' (live Overpass preview)"
    )
    allow_fallback_fixture: Optional[bool] = Field(
        default=True,
        description="Allow fallback to verified historical baseline fixture if remote historical archive is unreachable"
    )
    buffer_threshold_meters: Optional[float] = Field(
        default=30.0,
        description="Proximity buffer threshold in meters for critical facility assessment"
    )


@router.post("/analyze")
def start_infrastructure_analysis(req: InfrastructureAnalysisRequest) -> Dict[str, Any]:
    """
    Executes spatial intersection analysis between flood candidate polygons and OpenStreetMap infrastructure.
    Calculates potentially exposed buildings, roads (km), bridges, and healthcare facilities.
    """
    try:
        clean_id = validate_analysis_id(req.analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        summary = infrastructure_engine.execute_exposure_assessment(
            analysis_id=clean_id,
            osm_source=req.osm_source or "historical",
            allow_fallback_fixture=req.allow_fallback_fixture if req.allow_fallback_fixture is not None else True,
            buffer_threshold_meters=req.buffer_threshold_meters or 30.0
        )
        return summary
    except MissingFloodAnalysisError as e:
        raise HTTPException(status_code=404, detail=f"Flood analysis not found or invalid: {str(e)}")
    except HistoricalSnapshotUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Historical OSM data unavailable: {str(e)}")
    except InfrastructureError as e:
        raise HTTPException(status_code=500, detail=f"Infrastructure analysis failed: {str(e)}")


@router.get("/status/{analysis_id}")
def get_infrastructure_status(analysis_id: str) -> Dict[str, Any]:
    """
    Checks status and verifies existence of infrastructure exposure outputs for an analysis ID.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    summary_path = analysis_dir / "infrastructure_exposure.json"
    exposed_path = analysis_dir / "exposed_infrastructure.geojson"

    if not summary_path.exists() or not exposed_path.exists():
        return {
            "analysis_id": clean_id,
            "status": "NOT_ANALYZED",
            "outputs_ready": False,
            "provenance": None,
            "message": "Infrastructure exposure analysis has not been executed yet for this flood analysis."
        }

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted infrastructure summary on disk.")

    return {
        "analysis_id": clean_id,
        "status": summary.get("status", "COMPLETED"),
        "outputs_ready": True,
        "provenance": summary.get("provenance", "UNKNOWN"),
        "is_synthetic": summary.get("is_synthetic", False),
        "data_notice": summary.get("data_notice", ""),
        "osm_snapshot_date": summary.get("osm_snapshot_date", "2026-07-27"),
        "osm_attribution": summary.get("osm_attribution", OSM_ATTRIBUTION),
        "exposed_buildings_count": summary.get("exposed_buildings_count"),
        "exposed_building_area_sqm": summary.get("exposed_building_area_sqm"),
        "exposed_building_area_sqkm": summary.get("exposed_building_area_sqkm"),
        "exposed_road_length_km": summary.get("exposed_road_length_km"),
        "exposed_bridges_count": summary.get("exposed_bridges_count"),
        "critical_facilities_intersecting": summary.get("critical_facilities_intersecting"),
        "critical_facilities_in_buffer": summary.get("critical_facilities_in_buffer"),
        "blocker_reason": summary.get("blocker_reason"),
        "geojson_url": f"/api/infrastructure/layers/{clean_id}/exposed",
        "download_geojson": f"/api/infrastructure/download/{clean_id}/geojson",
        "download_summary": f"/api/infrastructure/download/{clean_id}/summary"
    }


@router.get("/summary/{analysis_id}")
def get_infrastructure_summary(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieves full exposure analysis summary metrics, facility status, and uncertainty details.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    summary_path = analysis_dir / "infrastructure_exposure.json"

    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Infrastructure summary for analysis ID '{clean_id}' not found. Run /api/infrastructure/analyze first."
        )

    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/layers/{analysis_id}/exposed")
def get_exposed_layer(analysis_id: str):
    """
    Returns GeoJSON FeatureCollection of all infrastructure features potentially exposed to candidate flood extent.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    exposed_path = analysis_dir / "exposed_infrastructure.geojson"

    if not exposed_path.exists() or exposed_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"Exposed infrastructure layer for '{clean_id}' not found.")

    with open(exposed_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/layers/{analysis_id}/baseline")
def get_baseline_layer(analysis_id: str):
    """
    Returns GeoJSON FeatureCollection of baseline pre-event infrastructure within the study area AOI.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    baseline_path = analysis_dir / "baseline_infrastructure.geojson"

    if not baseline_path.exists() or baseline_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"Baseline infrastructure layer for '{clean_id}' not found.")

    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/download/{analysis_id}/geojson")
def download_exposed_geojson(analysis_id: str):
    """
    Downloads the exposed infrastructure GeoJSON layer.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    exposed_path = analysis_dir / "exposed_infrastructure.geojson"

    if not exposed_path.exists() or exposed_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"Exposed GeoJSON for analysis '{clean_id}' not found.")

    return FileResponse(
        path=str(exposed_path),
        media_type="application/geo+json",
        filename=f"floodlens_{clean_id}_exposed_infrastructure.geojson"
    )


@router.get("/download/{analysis_id}/summary")
def download_summary_json(analysis_id: str):
    """
    Downloads the full machine-readable exposure summary JSON document.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except InfrastructureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    summary_path = analysis_dir / "infrastructure_exposure.json"

    if not summary_path.exists() or summary_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"Summary JSON for analysis '{clean_id}' not found.")

    return FileResponse(
        path=str(summary_path),
        media_type="application/json",
        filename=f"floodlens_{clean_id}_exposure_summary.json"
    )


@router.get("/osm/live-preview")
def get_live_osm_preview(bbox: Optional[str] = Query(None, description="Comma-separated bbox: min_lon,min_lat,max_lon,max_lat")):
    """
    Retrieves current OpenStreetMap infrastructure preview.
    Mandatory Rule: Labeled CURRENT_OSM_PREVIEW and not presented as historical pre-event data.
    """
    target_bbox = settings.DEFAULT_AOI_BBOX
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                target_bbox = parts
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Expected: min_lon,min_lat,max_lon,max_lat")

    try:
        preview_data = osm_client.fetch_current_preview(bbox=target_bbox)
        return preview_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Live preview query failed: {str(e)}")
