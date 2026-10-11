"""
Settlement Road Disconnection & Isolation Analysis API Router
FloodLens AI - Phase 5: Regional Hub Accessibility Modeling

Provides endpoints for:
1. Triggering network connectivity analysis on a validated Sentinel-1 flood analysis.
2. Polling analysis status and output readiness.
3. Retrieving detailed settlement accessibility summaries and detour metrics.
4. Serving GeoJSON layers for baseline routes, alternative paths, and closed road segments.
5. Downloading summary and route GeoJSON files with proper MIME types.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings, OUTPUTS_DIR
from app.core.infrastructure import validate_analysis_id, OSM_ATTRIBUTION
from app.core.connectivity import (
    connectivity_engine,
    ConnectivityError,
    MissingConnectivityInputError,
    DEFAULT_REGIONAL_HUBS,
    CANDIDATE_COMMUNITIES_TO_CHECK
)

router = APIRouter(prefix="/api/connectivity", tags=["Settlement Road Disconnection Analysis"])


class ConnectivityAnalysisRequest(BaseModel):
    analysis_id: str = Field(
        ...,
        description="ID of a validated Phase 3 Sentinel-1 flood analysis"
    )
    hubs: Optional[List[str]] = Field(
        default=None,
        description="Target regional hub names (default: Bidur, Trishuli Bazaar)"
    )
    candidate_communities: Optional[List[str]] = Field(
        default=None,
        description="Candidate settlement names to evaluate (default: Devighat, Battar, Tupche, Salme)"
    )
    closure_method: Optional[str] = Field(
        default="complete_severance",
        description="Road closure simulation rule: 'complete_severance' or 'bridge_severance_only'"
    )
    snapping_tolerance_m: Optional[float] = Field(
        default=50.0,
        description="Road node snapping tolerance in meters for graph construction"
    )
    max_settlement_snap_distance_m: Optional[float] = Field(
        default=1000.0,
        description="Maximum permitted distance (meters) to snap settlements to road nodes"
    )
    osm_source: Optional[str] = Field(
        default="historical",
        description="Source of OSM infrastructure: 'historical' (2026-07-27 baseline) or 'current_preview'"
    )
    allow_fallback_fixture: Optional[bool] = Field(
        default=True,
        description="Allow fallback to verified historical baseline fixture if remote historical archive is unreachable"
    )


@router.post("/analyze")
def start_connectivity_analysis(req: ConnectivityAnalysisRequest) -> Dict[str, Any]:
    """
    Executes topological road-network graph construction and Dijkstra accessibility routing.
    Models baseline connectivity, simulates candidate flood closures, and categorizes settlements.
    """
    try:
        clean_id = validate_analysis_id(req.analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if req.snapping_tolerance_m is not None and req.snapping_tolerance_m < 0:
        raise HTTPException(status_code=400, detail="Snapping tolerance must be non-negative.")

    if req.max_settlement_snap_distance_m is not None and req.max_settlement_snap_distance_m < 0:
        raise HTTPException(status_code=400, detail="Maximum settlement snap distance must be non-negative.")

    try:
        summary = connectivity_engine.execute_connectivity_assessment(
            analysis_id=clean_id,
            hubs=req.hubs,
            candidate_communities=req.candidate_communities,
            closure_method=req.closure_method or "complete_severance",
            snapping_tolerance_m=req.snapping_tolerance_m if req.snapping_tolerance_m is not None else 50.0,
            max_settlement_snap_distance_m=req.max_settlement_snap_distance_m if req.max_settlement_snap_distance_m is not None else 1000.0,
            osm_source=req.osm_source or "historical",
            allow_fallback_fixture=req.allow_fallback_fixture if req.allow_fallback_fixture is not None else True
        )
        return summary
    except MissingConnectivityInputError as e:
        raise HTTPException(status_code=404, detail=f"Input data missing or invalid: {str(e)}")
    except ConnectivityError as e:
        raise HTTPException(status_code=500, detail=f"Connectivity analysis failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected connectivity error: {str(e)}")


@router.get("/status/{analysis_id}")
def get_connectivity_status(analysis_id: str) -> Dict[str, Any]:
    """
    Checks status and verifies existence of road connectivity outputs for an analysis ID.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    summary_path = analysis_dir / "connectivity_summary.json"
    routes_path = analysis_dir / "connectivity_routes.geojson"

    if not summary_path.exists() or not routes_path.exists():
        return {
            "analysis_id": clean_id,
            "status": "NOT_ANALYZED",
            "outputs_ready": False,
            "provenance": None,
            "message": "Settlement road disconnection analysis has not been executed yet for this flood analysis."
        }

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted connectivity summary on disk.")

    counts = summary.get("summary_counts", {})
    return {
        "analysis_id": clean_id,
        "status": summary.get("status", "COMPLETED"),
        "outputs_ready": True,
        "provenance": summary.get("provenance", "UNKNOWN"),
        "is_synthetic": summary.get("is_synthetic", False),
        "data_notice": summary.get("data_notice", ""),
        "settlements_evaluated": counts.get("settlements_evaluated", 0),
        "newly_disconnected": counts.get("newly_disconnected", 0),
        "already_disconnected": counts.get("already_disconnected_at_baseline", 0),
        "detoured": counts.get("detoured", 0),
        "route_unchanged": counts.get("route_unchanged", 0),
        "unavailable": counts.get("unavailable", 0),
        "snap_failed": counts.get("snap_failed", 0),
        "closed_edges_count": summary.get("closure_parameters", {}).get("closed_edges_count", 0),
        "closed_bridges_count": summary.get("closure_parameters", {}).get("closed_bridges_count", 0),
        "routes_geojson_url": f"/api/connectivity/layers/{clean_id}/routes",
        "closed_roads_url": f"/api/connectivity/layers/{clean_id}/closed_roads",
        "download_summary": f"/api/connectivity/download/{clean_id}/summary",
        "download_routes": f"/api/connectivity/download/{clean_id}/routes"
    }


@router.get("/summary/{analysis_id}")
def get_connectivity_summary(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieves full road connectivity summary metrics, settlement statuses, and uncertainty details.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    summary_path = analysis_dir / "connectivity_summary.json"

    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Connectivity summary for analysis ID '{clean_id}' not found. Run /api/connectivity/analyze first."
        )

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading connectivity summary from disk.")


@router.get("/routes/{analysis_id}")
def get_connectivity_routes(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieves GeoJSON feature collection of baseline routes, post-flood routes, closed edges, and settlement nodes.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    routes_path = analysis_dir / "connectivity_routes.geojson"

    if not routes_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Route GeoJSON for analysis ID '{clean_id}' not found. Run /api/connectivity/analyze first."
        )

    try:
        with open(routes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading route GeoJSON from disk.")


@router.get("/layers/{analysis_id}/{layer_type}")
def get_connectivity_layer(analysis_id: str, layer_type: str) -> Dict[str, Any]:
    """
    Serves specialized GeoJSON layers for Leaflet dashboard rendering ('routes', 'closed_roads').
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id

    if layer_type == "routes":
        file_path = analysis_dir / "connectivity_routes.geojson"
    elif layer_type == "closed_roads":
        file_path = analysis_dir / "closed_roads.geojson"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid layer type '{layer_type}'. Use 'routes' or 'closed_roads'.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer '{layer_type}' for analysis '{clean_id}' not found.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail=f"Failed to load layer '{layer_type}' from disk.")


@router.get("/download/{analysis_id}/{file_type}")
def download_connectivity_file(analysis_id: str, file_type: str):
    """
    Downloads connectivity summary JSON or route GeoJSON files.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id

    if file_type == "summary":
        target = analysis_dir / "connectivity_summary.json"
        media_type = "application/json"
        filename = f"connectivity_summary_{clean_id}.json"
    elif file_type == "routes":
        target = analysis_dir / "connectivity_routes.geojson"
        media_type = "application/geo+json"
        filename = f"connectivity_routes_{clean_id}.geojson"
    elif file_type == "closed_roads":
        target = analysis_dir / "closed_roads.geojson"
        media_type = "application/geo+json"
        filename = f"closed_roads_{clean_id}.geojson"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{file_type}'. Use 'summary', 'routes', or 'closed_roads'.")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Requested file '{file_type}' for analysis '{clean_id}' does not exist.")

    return FileResponse(
        path=str(target),
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
