"""
API integration tests for flood analysis execution, status polling, metadata retrieval,
and GeoTIFF / GeoJSON file downloads.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_start_flood_analysis_and_poll_status():
    payload = {
        "analysis_id": "test-trishuli-unit-01",
        "pre_scene": {
            "id": "s1-pre-test",
            "name": "S1D_IW_GRDH_20260731T001843",
            "acquisition_date": "2026-07-31T00:18:43Z",
            "orbit_pass": "DESCENDING",
            "relative_orbit": 121,
            "polarization": "VV&VH"
        },
        "post_scene": {
            "id": "s1-post-test",
            "name": "S1D_IW_GRDH_20260812T001844",
            "acquisition_date": "2026-08-12T00:18:44Z",
            "orbit_pass": "DESCENDING",
            "relative_orbit": 121,
            "polarization": "VV&VH"
        },
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "parameters": {
            "threshold_db": -3.2,
            "min_water_backscatter_db": -14.0,
            "slope_threshold_deg": 15.0,
            "filter_kernel_size": 3,
            "min_polygon_pixels": 3,
            "target_crs": "EPSG:4326"
        },
        "is_demo": True
    }

    # 1. Trigger analysis
    response = client.post("/api/flood/analyze", json=payload)
    assert response.status_code == 200
    meta = response.json()
    assert meta["analysis_id"] == "test-trishuli-unit-01"
    assert meta["status"] == "COMPLETED"
    assert "area_statistics" in meta
    assert meta["area_statistics"]["candidate_flood_area_sqkm"] > 0
    assert "warnings_and_uncertainties" in meta

    # 2. Check status endpoint
    status_res = client.get("/api/flood/status/test-trishuli-unit-01")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["outputs_ready"] is True
    assert status_data["status"] == "COMPLETED"

    # 3. Retrieve metadata
    meta_res = client.get("/api/flood/metadata/test-trishuli-unit-01")
    assert meta_res.status_code == 200
    assert meta_res.json()["analysis_id"] == "test-trishuli-unit-01"

    # 4. Download GeoTIFF
    tif_res = client.get("/api/flood/download/test-trishuli-unit-01/geotiff")
    assert tif_res.status_code == 200
    assert tif_res.headers["content-type"] == "image/tiff"
    assert len(tif_res.content) > 500

    # 5. Download GeoJSON
    geojson_res = client.get("/api/flood/download/test-trishuli-unit-01/geojson")
    assert geojson_res.status_code == 200
    geojson_data = geojson_res.json()
    assert geojson_data["type"] == "FeatureCollection"
    assert len(geojson_data["features"]) > 0


def test_start_flood_analysis_incompatible_pair():
    payload = {
        "analysis_id": "test-incompatible-pair",
        "pre_scene": {
            "id": "s1-pre",
            "orbit_pass": "ASCENDING"
        },
        "post_scene": {
            "id": "s1-post",
            "orbit_pass": "DESCENDING"
        },
        "bbox": [85.05, 27.75, 85.25, 27.95]
    }
    response = client.post("/api/flood/analyze", json=payload)
    assert response.status_code == 400
    assert "Incompatible" in response.json()["detail"]


def test_get_analysis_status_not_found():
    response = client.get("/api/flood/status/non-existent-id-999")
    assert response.status_code == 404


def test_start_flood_analysis_missing_measurements_non_demo():
    payload = {
        "analysis_id": "test-missing-real-data",
        "pre_scene": {
            "id": "s1-real-id-1",
            "name": "S1D_IW_GRDH_20260731T001843",
            "acquisition_date": "2026-07-31T00:18:43Z",
            "orbit_pass": "DESCENDING",
            "relative_orbit": 121
        },
        "post_scene": {
            "id": "s1-real-id-2",
            "name": "S1D_IW_GRDH_20260812T001844",
            "acquisition_date": "2026-08-12T00:18:44Z",
            "orbit_pass": "DESCENDING",
            "relative_orbit": 121
        },
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "is_demo": False  # Enforce real measurement requirement
    }
    response = client.post("/api/flood/analyze", json=payload)
    assert response.status_code == 422
    assert "Missing measurement files" in response.json()["detail"]
