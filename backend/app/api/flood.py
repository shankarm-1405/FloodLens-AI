"""
Flood Inundation Analysis API Router
Endpoints for executing Sentinel-1 SAR change detection, checking analysis progress,
retrieving calculated flood metrics, and downloading georeferenced GeoTIFF and GeoJSON masks.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings, OUTPUTS_DIR
from app.core.sar_processor import (
    sar_processor,
    SARProcessingParameters,
    IncompatiblePairError,
    ImageGridMismatchError,
    MissingMeasurementFilesError,
    SARProcessingError
)
from app.core.copernicus import copernicus_client, InvalidCoordinatesError

router = APIRouter(prefix="/api/flood", tags=["Flood Extent Extraction"])


class FloodAnalysisRequest(BaseModel):
    analysis_id: Optional[str] = Field(
        default=None,
        description="Optional unique analysis ID; auto-generated if omitted"
    )
    pre_scene: Dict[str, Any] = Field(
        ...,
        description="Pre-event Sentinel-1 acquisition metadata object"
    )
    post_scene: Dict[str, Any] = Field(
        ...,
        description="Post-event Sentinel-1 acquisition metadata object"
    )
    bbox: Optional[List[float]] = Field(
        default=None,
        description="Geographic bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    parameters: Optional[SARProcessingParameters] = Field(
        default_factory=SARProcessingParameters,
        description="Configurable processing parameters (threshold, slope, filter size)"
    )
    is_demo: Optional[bool] = Field(
        default=None,
        description="Explicit flag for demonstration fixture mode"
    )


import re

def validate_analysis_id(analysis_id: str) -> str:
    """
    Sanitizes and enforces safe format for analysis IDs, preventing directory traversal.
    """
    if not re.match(r"^[a-zA-Z0-9_\-]+$", analysis_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid analysis ID: must contain only alphanumeric characters, dashes, and underscores."
        )
    resolved = (OUTPUTS_DIR / analysis_id).resolve()
    try:
        resolved.relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt detected in analysis ID.")
    return analysis_id


@router.post("/analyze")
def start_flood_analysis(req: FloodAnalysisRequest) -> Dict[str, Any]:
    """
    Executes Sentinel-1 amplitude change detection between validated pre- and post-event scenes.
    Generates georeferenced GeoTIFF, GeoJSON vectors, and scientific metadata.
    """
    target_bbox = req.bbox if req.bbox is not None else settings.DEFAULT_AOI_BBOX
    try:
        copernicus_client.validate_aoi_bbox(target_bbox)
    except InvalidCoordinatesError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_id = req.analysis_id or f"fl-{uuid.uuid4().hex[:10]}"
    validate_analysis_id(analysis_id)
    params = req.parameters or SARProcessingParameters()

    is_demo_mode = req.is_demo if req.is_demo is not None else settings.DEMO_MODE

    try:
        metadata = sar_processor.execute_flood_analysis(
            analysis_id=analysis_id,
            pre_scene=req.pre_scene,
            post_scene=req.post_scene,
            bbox=target_bbox,
            params=params,
            is_demo_mode=is_demo_mode
        )
        return metadata
    except IncompatiblePairError as e:
        raise HTTPException(status_code=400, detail=f"Incompatible satellite pair: {str(e)}")
    except ImageGridMismatchError as e:
        raise HTTPException(status_code=400, detail=f"Raster grid mismatch: {str(e)}")
    except MissingMeasurementFilesError as e:
        raise HTTPException(status_code=422, detail=f"Missing measurement files: {str(e)}")
    except SARProcessingError as e:
        raise HTTPException(status_code=500, detail=f"SAR processing failed: {str(e)}")


@router.get("/status/{analysis_id}")
def get_analysis_status(analysis_id: str) -> Dict[str, Any]:
    """
    Checks status and verifies existence of output rasters for a given analysis ID.
    """
    clean_id = validate_analysis_id(analysis_id)
    analysis_dir = OUTPUTS_DIR / clean_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    metadata_path = analysis_dir / "analysis_metadata.json"
    geotiff_path = analysis_dir / "flood_candidate_mask.tif"
    geojson_path = analysis_dir / "flood_candidate_mask.geojson"

    geotiff_exists = geotiff_path.exists() and geotiff_path.stat().st_size > 0
    geojson_exists = geojson_path.exists() and geojson_path.stat().st_size > 0

    if not metadata_path.exists() or not geotiff_exists:
        return {
            "analysis_id": clean_id,
            "status": "PROCESSING",
            "outputs_ready": False
        }

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted analysis metadata on disk.")

    return {
        "analysis_id": clean_id,
        "status": "COMPLETED",
        "outputs_ready": True,
        "is_demo_fixture": metadata.get("is_demo_fixture", False),
        "candidate_flood_area_sqkm": metadata.get("area_statistics", {}).get("candidate_flood_area_sqkm", 0.0),
        "valid_coverage_ratio": metadata.get("area_statistics", {}).get("valid_coverage_ratio", 0.0),
        "geotiff_download": f"/api/flood/download/{clean_id}/geotiff",
        "geojson_download": f"/api/flood/download/{clean_id}/geojson",
        "pre_preview": f"/api/flood/preview/{clean_id}/pre",
        "post_preview": f"/api/flood/preview/{clean_id}/post",
        "diff_preview": f"/api/flood/preview/{clean_id}/diff",
        "mask_preview": f"/api/flood/preview/{clean_id}/mask"
    }


@router.get("/metadata/{analysis_id}")
def get_analysis_metadata(analysis_id: str) -> Dict[str, Any]:
    """
    Retrieves full scientific metadata, parameters, and computed statistics for an analysis ID.
    """
    clean_id = validate_analysis_id(analysis_id)
    analysis_dir = OUTPUTS_DIR / clean_id
    metadata_path = analysis_dir / "analysis_metadata.json"

    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail=f"Metadata for analysis ID '{clean_id}' not found.")

    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/preview/{analysis_id}/{kind}")
def get_analysis_preview(analysis_id: str, kind: str):
    """
    Returns visual PNG thumbnails of SAR backscatter (pre, post, diff, mask).
    """
    clean_id = validate_analysis_id(analysis_id)
    valid_kinds = {
        "pre": "pre_preview.png",
        "post": "post_preview.png",
        "diff": "diff_preview.png",
        "mask": "mask_preview.png"
    }
    if kind not in valid_kinds:
        raise HTTPException(status_code=400, detail=f"Invalid preview kind '{kind}'. Expected one of: {list(valid_kinds.keys())}")

    preview_path = OUTPUTS_DIR / clean_id / valid_kinds[kind]
    if not preview_path.exists() or preview_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"Preview image for '{kind}' not found in analysis '{clean_id}'.")

    return FileResponse(
        path=str(preview_path),
        media_type="image/png",
        filename=f"floodlens_{clean_id}_{kind}.png"
    )


@router.get("/download/{analysis_id}/geotiff")
def download_geotiff(analysis_id: str):
    """
    Downloads the georeferenced flood-candidate GeoTIFF raster.
    """
    clean_id = validate_analysis_id(analysis_id)
    analysis_dir = OUTPUTS_DIR / clean_id
    geotiff_path = analysis_dir / "flood_candidate_mask.tif"

    if not geotiff_path.exists() or geotiff_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"GeoTIFF for analysis ID '{clean_id}' not found.")

    return FileResponse(
        path=str(geotiff_path),
        media_type="image/tiff",
        filename=f"floodlens_{clean_id}_flood_mask.tif"
    )


@router.get("/download/{analysis_id}/geojson")
def download_geojson(analysis_id: str):
    """
    Downloads or renders the vectorized flood-candidate GeoJSON layer.
    """
    clean_id = validate_analysis_id(analysis_id)
    analysis_dir = OUTPUTS_DIR / clean_id
    geojson_path = analysis_dir / "flood_candidate_mask.geojson"

    if not geojson_path.exists() or geojson_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail=f"GeoJSON for analysis ID '{clean_id}' not found.")

    return FileResponse(
        path=str(geojson_path),
        media_type="application/geo+json",
        filename=f"floodlens_{clean_id}_flood_layer.geojson"
    )
