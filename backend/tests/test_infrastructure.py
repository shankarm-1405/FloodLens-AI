"""
Tests for Phase 4: Historical OSM Infrastructure Exposure Assessment
FloodLens AI - Trishuli River Corridor, Nepal

Validates:
- Historical snapshot date handling and validation
- Missing or unavailable historical data (blocker reporting, no fabricated zeros)
- Current-data fallback labeling (CURRENT_OSM_PREVIEW vs pre-event historical)
- AOI clipping and geometry validation (make_valid)
- Building polygon intersections and area metrics (m² and km²)
- Road intersection length calculations (km) and units
- Bridge and healthcare facility counting and proximity classification
- Duplicate OSM ID deduplication and double-count prevention
- Missing flood GeoJSON and path-traversal analysis ID rejection
- Synthetic vs real provenance labels (SYNTHETIC_TEST_FIXTURE)
- API endpoint responses, downloads, and layer delivery
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, box, mapping
import geopandas as gpd

from app.main import app
from app.config import OUTPUTS_DIR, settings
from app.core.infrastructure import (
    osm_client,
    infrastructure_engine,
    validate_analysis_id,
    InfrastructureError,
    HistoricalSnapshotUnavailableError,
    MissingFloodAnalysisError,
    OSMInfrastructureClient,
    InfrastructureExposureEngine,
    OSM_ATTRIBUTION,
    PROJECTED_CRS_NEPAL
)
from app.fixtures.osm_trishuli_fixture import HISTORICAL_TRISHULI_OSM_FIXTURE

client = TestClient(app)


# --- 1. HISTORICAL SNAPSHOT DATE & RETRIEVAL VALIDATION ---

def test_historical_snapshot_date_and_attribution():
    """Verifies default snapshot date is anchored to pre-event 2026-07-27 and attribution is present."""
    client_inst = OSMInfrastructureClient()
    assert client_inst.default_snapshot_date == "2026-07-27"
    assert "OpenStreetMap contributors" in client_inst.attribution
    assert client_inst.attribution == OSM_ATTRIBUTION


def test_aoi_bbox_validation():
    """Verifies bounding box validation rules."""
    client_inst = OSMInfrastructureClient()
    # Valid Trishuli bbox
    client_inst.validate_aoi_bbox([85.05, 27.75, 85.25, 27.95])

    # Invalid coordinates
    with pytest.raises(ValueError, match="Invalid longitude span"):
        client_inst.validate_aoi_bbox([85.25, 27.75, 85.05, 27.95])

    with pytest.raises(ValueError, match="Invalid latitude span"):
        client_inst.validate_aoi_bbox([85.05, 95.0, 85.25, 27.95])

    with pytest.raises(ValueError, match="must be a list of 4 coordinates"):
        client_inst.validate_aoi_bbox([85.05, 27.75])


def test_aoi_clipping():
    """Tests spatial clipping of GeoJSON features against the target AOI bounding box."""
    client_inst = OSMInfrastructureClient()
    # Feature 1: Inside [85.05, 27.75, 85.25, 27.95]
    # Feature 2: Far outside (Kathmandu: 85.32, 27.71)
    sample_fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"osm_id": 1, "name": "Inside Trishuli"},
                "geometry": {"type": "Point", "coordinates": [85.15, 27.85]}
            },
            {
                "type": "Feature",
                "properties": {"osm_id": 2, "name": "Outside Kathmandu"},
                "geometry": {"type": "Point", "coordinates": [85.35, 27.70]}
            }
        ]
    }
    clipped = client_inst.clip_geojson_to_bbox(sample_fc, [85.05, 27.75, 85.25, 27.95])
    assert len(clipped["features"]) == 1
    assert clipped["features"][0]["properties"]["osm_id"] == 1


# --- 2. GEOMETRY VALIDATION & REPAIR ---

def test_geometry_validation_and_repair():
    """Tests that invalid geometries are repaired via make_valid and empty ones dropped."""
    client_inst = OSMInfrastructureClient()
    # Create bowtie self-intersecting polygon (invalid)
    bowtie_coords = [[[0, 0], [0, 2], [2, 0], [2, 2], [0, 0]]]
    features = [
        {
            "type": "Feature",
            "properties": {"osm_id": 10},
            "geometry": {"type": "Polygon", "coordinates": bowtie_coords}
        },
        {
            "type": "Feature",
            "properties": {"osm_id": 20},
            "geometry": {"type": "Polygon", "coordinates": []}  # Empty/invalid
        },
        {
            "type": "Feature",
            "properties": {"osm_id": 30},
            "geometry": {"type": "Point", "coordinates": [85.15, 27.85]}  # Valid point
        }
    ]
    cleaned, valid_cnt, rep_cnt, drop_cnt = client_inst.validate_and_clean_geometries(features)
    assert valid_cnt == 1  # The point
    assert rep_cnt == 1    # The bowtie polygon was repaired
    assert drop_cnt == 1   # The empty coordinates dropped
    assert len(cleaned) == 2


# --- 3. MISSING OR UNAVAILABLE HISTORICAL DATA (NO FABRICATED ZEROS) ---

def test_unavailable_historical_snapshot_without_fallback():
    """
    Historical-data rule: If remote historical snapshot is unavailable and fallback fixture is disabled,
    must raise HistoricalSnapshotUnavailableError and NOT fabricate zero counts.
    """
    client_inst = OSMInfrastructureClient()
    # Force live attempt on unroutable date/host without fixture fallback
    with pytest.raises(HistoricalSnapshotUnavailableError) as exc_info:
        client_inst.fetch_historical_infrastructure(
            bbox=[85.05, 27.75, 85.25, 27.95],
            snapshot_date="2026-07-27",
            force_live=True,
            allow_fallback_fixture=False,
            timeout=1
        )
    assert "Historical OSM snapshot for 2026-07-27 is unavailable" in str(exc_info.value)


def test_exposure_engine_reports_blocker_when_historical_unavailable(tmp_path, monkeypatch):
    """
    Verifies that when historical data is completely unavailable, the engine reports
    a BLOCKED status with null metrics, never returning fabricated zeros.
    """
    engine = InfrastructureExposureEngine()
    # Monkeypatch osm_client to raise HistoricalSnapshotUnavailableError
    def mock_fetch(*args, **kwargs):
        raise HistoricalSnapshotUnavailableError("Remote Ohsome API gateway timeout.")
    
    monkeypatch.setattr(engine.osm_client, "fetch_historical_infrastructure", mock_fetch)

    # Use existing e2e-trishuli-aug2026 analysis
    result = engine.execute_exposure_assessment("e2e-trishuli-aug2026", allow_fallback_fixture=False)
    assert result["status"] == "BLOCKED"
    assert result["provenance"] in ("UNAVAILABLE", "HISTORICAL_SNAPSHOT_UNAVAILABLE")
    assert result["exposed_buildings_count"] is None
    assert result["exposed_road_length_km"] is None
    assert result["exposed_bridges_count"] is None
    assert "Remote Ohsome API gateway timeout." in result["blocker_reason"]


# --- 4. CURRENT-DATA FALLBACK LABELING ---

def test_current_preview_provenance_labeling():
    """
    Verifies that live current preview features are labeled CURRENT_OSM_PREVIEW and
    include an explicit notice that they are NOT pre-event historical data.
    """
    client_inst = OSMInfrastructureClient()
    # Mock overpass response
    mock_overpass = {
        "elements": [
            {
                "type": "node",
                "id": 9999,
                "lat": 27.85,
                "lon": 85.15,
                "tags": {"amenity": "hospital", "name": "Current Hospital"}
            }
        ]
    }
    converted = client_inst._convert_overpass_to_geojson(
        mock_overpass, "2026-10-10T00:00:00Z", [85.05, 27.75, 85.25, 27.95], "CURRENT_OSM_PREVIEW"
    )
    assert converted["metadata"]["provenance"] == "CURRENT_OSM_PREVIEW"
    assert len(converted["features"]) == 1
    assert converted["features"][0]["properties"]["osm_id"] == 9999


# --- 5. SPATIAL INTERSECTIONS, AREAS, AND LENGTHS (UTM ZONE 45N) ---

def test_building_polygon_intersection_and_area(tmp_path):
    """
    Tests building footprint intersections and metric area calculation in UTM Zone 45N (EPSG:32645).
    """
    # Create synthetic analysis directory with 1 flood polygon and 2 buildings
    test_id = "test-building-area-calc"
    test_dir = OUTPUTS_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Flood polygon covering [85.150, 27.850] to [85.155, 27.855]
        flood_poly = box(85.150, 27.850, 85.155, 27.855)
        flood_fc = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": mapping(flood_poly), "properties": {}}]
        }
        with open(test_dir / "flood_candidate_mask.geojson", "w") as f:
            json.dump(flood_fc, f)

        meta = {
            "analysis_id": test_id,
            "status": "COMPLETED",
            "is_demo_fixture": True,
            "area_of_interest": {"bbox": [85.05, 27.75, 85.25, 27.95]}
        }
        with open(test_dir / "analysis_metadata.json", "w") as f:
            json.dump(meta, f)

        # Building 1: Inside flood polygon (0.002 x 0.002 deg)
        b1_geom = box(85.151, 27.851, 85.153, 27.853)
        # Building 2: Far outside flood polygon
        b2_geom = box(85.180, 27.880, 85.182, 27.882)

        test_osm = {
            "type": "FeatureCollection",
            "metadata": {"snapshot_date": "2026-07-27", "attribution": OSM_ATTRIBUTION},
            "features": [
                {
                    "type": "Feature",
                    "properties": {"osm_id": 501, "category": "building", "name": "Flooded House"},
                    "geometry": mapping(b1_geom)
                },
                {
                    "type": "Feature",
                    "properties": {"osm_id": 502, "category": "building", "name": "Safe House"},
                    "geometry": mapping(b2_geom)
                }
            ]
        }

        engine = InfrastructureExposureEngine()
        # Mock fetch to return test_osm
        engine.osm_client.fetch_historical_infrastructure = lambda *args, **kwargs: test_osm

        summary = engine.execute_exposure_assessment(test_id)
        assert summary["exposed_buildings_count"] == 1
        assert summary["exposed_building_area_sqm"] > 0
        assert summary["exposed_building_area_sqkm"] > 0
        assert summary["provenance"] == "SYNTHETIC_TEST_FIXTURE"

    finally:
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_road_intersection_length_in_km():
    """
    Tests road centerline intersection and length measurement in kilometres.
    """
    test_id = "test-road-length-calc"
    test_dir = OUTPUTS_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Flood box: 85.150 to 85.160 (~984m wide)
        flood_poly = box(85.150, 27.850, 85.160, 27.860)
        flood_fc = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": mapping(flood_poly), "properties": {}}]
        }
        with open(test_dir / "flood_candidate_mask.geojson", "w") as f:
            json.dump(flood_fc, f)

        meta = {
            "analysis_id": test_id,
            "status": "COMPLETED",
            "is_demo_fixture": True,
            "area_of_interest": {"bbox": [85.05, 27.75, 85.25, 27.95]}
        }
        with open(test_dir / "analysis_metadata.json", "w") as f:
            json.dump(meta, f)

        # Road crossing straight through the flood box from 85.140 to 85.170 (lat 27.855)
        # Intersected span is 85.150 to 85.160 (0.01 deg lon ≈ 0.985 km)
        road_line = LineString([(85.140, 27.855), (85.170, 27.855)])

        test_osm = {
            "type": "FeatureCollection",
            "metadata": {"snapshot_date": "2026-07-27", "attribution": OSM_ATTRIBUTION},
            "features": [
                {
                    "type": "Feature",
                    "properties": {"osm_id": 701, "category": "road", "name": "Trishuli Highway Section"},
                    "geometry": mapping(road_line)
                }
            ]
        }

        engine = InfrastructureExposureEngine()
        engine.osm_client.fetch_historical_infrastructure = lambda *args, **kwargs: test_osm

        summary = engine.execute_exposure_assessment(test_id)
        assert summary["exposed_road_length_km"] is not None
        # Should be approximately 0.985 km
        assert 0.90 <= summary["exposed_road_length_km"] <= 1.05

    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_bridge_and_facility_proximity_classification():
    """
    Tests bridge detection and 3-tier critical facility classification:
    (DIRECTLY_INTERSECTING, BUFFER_ZONE_30M, SAFE_ELEVATED).
    """
    test_id = "test-bridge-facility-calc"
    test_dir = OUTPUTS_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        flood_poly = box(85.150, 27.850, 85.155, 27.855)
        flood_fc = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": mapping(flood_poly), "properties": {}}]
        }
        with open(test_dir / "flood_candidate_mask.geojson", "w") as f:
            json.dump(flood_fc, f)

        meta = {
            "analysis_id": test_id,
            "status": "COMPLETED",
            "is_demo_fixture": True,
            "area_of_interest": {"bbox": [85.05, 27.75, 85.25, 27.95]}
        }
        with open(test_dir / "analysis_metadata.json", "w") as f:
            json.dump(meta, f)

        # 1 bridge intersecting
        br1 = LineString([(85.148, 27.852), (85.152, 27.852)])
        # Facility 1: Inside flood
        fac_in = Point(85.151, 27.851)
        # Facility 2: ~15-20 meters from flood edge (85.155 is boundary, 0.00015 deg ≈ 15m)
        fac_buffer = Point(85.15515, 27.852)
        # Facility 3: > 500 meters away
        fac_safe = Point(85.170, 27.852)

        test_osm = {
            "type": "FeatureCollection",
            "metadata": {"snapshot_date": "2026-07-27", "attribution": OSM_ATTRIBUTION},
            "features": [
                {
                    "type": "Feature",
                    "properties": {"osm_id": 801, "category": "bridge", "name": "Trishuli River Bridge"},
                    "geometry": mapping(br1)
                },
                {
                    "type": "Feature",
                    "properties": {"osm_id": 901, "category": "healthcare", "name": "Inundated Clinic"},
                    "geometry": mapping(fac_in)
                },
                {
                    "type": "Feature",
                    "properties": {"osm_id": 902, "category": "healthcare", "name": "Buffer Health Post"},
                    "geometry": mapping(fac_buffer)
                },
                {
                    "type": "Feature",
                    "properties": {"osm_id": 903, "category": "healthcare", "name": "Safe Hospital"},
                    "geometry": mapping(fac_safe)
                }
            ]
        }

        engine = InfrastructureExposureEngine()
        engine.osm_client.fetch_historical_infrastructure = lambda *args, **kwargs: test_osm

        summary = engine.execute_exposure_assessment(test_id)
        assert summary["exposed_bridges_count"] == 1
        assert summary["critical_facilities_assessed"] == 3
        assert summary["critical_facilities_intersecting"] == 1
        assert summary["critical_facilities_in_buffer"] == 1

        details = {d["name"]: d for d in summary["critical_facilities_details"]}
        assert details["Inundated Clinic"]["exposure_status"] == "DIRECTLY_INTERSECTING"
        assert details["Buffer Health Post"]["exposure_status"] == "BUFFER_ZONE_30M"
        assert details["Safe Hospital"]["exposure_status"] == "SAFE_ELEVATED"

    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


# --- 6. DUPLICATE OSM IDS AND DOUBLE-COUNT PREVENTION ---

def test_duplicate_osm_ids_deduplication():
    """
    Tests that duplicated OSM IDs in input datasets are deduplicated and not counted twice.
    """
    test_id = "test-duplicate-osm-ids"
    test_dir = OUTPUTS_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        flood_poly = box(85.150, 27.850, 85.155, 27.855)
        flood_fc = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": mapping(flood_poly), "properties": {}}]
        }
        with open(test_dir / "flood_candidate_mask.geojson", "w") as f:
            json.dump(flood_fc, f)

        meta = {
            "analysis_id": test_id,
            "status": "COMPLETED",
            "is_demo_fixture": True,
            "area_of_interest": {"bbox": [85.05, 27.75, 85.25, 27.95]}
        }
        with open(test_dir / "analysis_metadata.json", "w") as f:
            json.dump(meta, f)

        b1_geom = box(85.151, 27.851, 85.153, 27.853)

        # Same building provided twice with identical osm_id: 1001
        test_osm = {
            "type": "FeatureCollection",
            "metadata": {"snapshot_date": "2026-07-27", "attribution": OSM_ATTRIBUTION},
            "features": [
                {
                    "type": "Feature",
                    "properties": {"osm_id": 1001, "category": "building", "name": "House A"},
                    "geometry": mapping(b1_geom)
                },
                {
                    "type": "Feature",
                    "properties": {"osm_id": 1001, "category": "building", "name": "House A Duplicate"},
                    "geometry": mapping(b1_geom)
                }
            ]
        }

        engine = InfrastructureExposureEngine()
        engine.osm_client.fetch_historical_infrastructure = lambda *args, **kwargs: test_osm

        summary = engine.execute_exposure_assessment(test_id)
        # Should count only 1 building despite 2 identical entries
        assert summary["exposed_buildings_count"] == 1

    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


# --- 7. PATH TRAVERSAL AND SECURITY ENFORCEMENT ---

def test_path_traversal_in_analysis_id_rejected():
    """Verifies path traversal attempts in analysis ID are strictly rejected."""
    traversal_ids = [
        "../etc/passwd",
        "..\\windows\\system32",
        "sub/dir/test",
        "test;rm -rf",
        "test..payload"
    ]
    for bad_id in traversal_ids:
        with pytest.raises(InfrastructureError):
            validate_analysis_id(bad_id)

        # GET status endpoint either returns 400 (if handled) or 404 (if routing doesn't match slashes)
        resp = client.get(f"/api/infrastructure/status/{bad_id}")
        assert resp.status_code in (400, 404)

        # POST analyze body receives bad_id directly and returns 400
        post_resp = client.post("/api/infrastructure/analyze", json={"analysis_id": bad_id})
        assert post_resp.status_code == 400


# --- 8. API ENDPOINTS INTEGRATION ---

def test_api_analyze_and_status_e2e():
    """Tests POST /api/infrastructure/analyze and GET /api/infrastructure/status on e2e fixture."""
    # Analyze existing e2e fixture
    resp = client.post("/api/infrastructure/analyze", json={
        "analysis_id": "e2e-trishuli-aug2026",
        "osm_source": "historical",
        "allow_fallback_fixture": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == "e2e-trishuli-aug2026"
    assert data["status"] == "COMPLETED"
    assert data["provenance"] == "SYNTHETIC_TEST_FIXTURE"
    assert data["is_synthetic"] is True
    assert "OpenStreetMap contributors" in data["osm_attribution"]
    assert data["exposed_buildings_count"] == 3
    assert data["exposed_bridges_count"] == 1
    assert data["exposed_road_length_km"] > 0

    # Status check
    status_resp = client.get("/api/infrastructure/status/e2e-trishuli-aug2026")
    assert status_resp.status_code == 200
    s_data = status_resp.json()
    assert s_data["status"] == "COMPLETED"
    assert s_data["outputs_ready"] is True
    assert s_data["exposed_buildings_count"] == 3


def test_api_layers_and_downloads():
    """Tests GET /api/infrastructure/layers and download endpoints."""
    # Exposed GeoJSON layer
    layer_resp = client.get("/api/infrastructure/layers/e2e-trishuli-aug2026/exposed")
    assert layer_resp.status_code == 200
    layer_json = layer_resp.json()
    assert layer_json["type"] == "FeatureCollection"
    assert len(layer_json["features"]) > 0

    # Baseline GeoJSON layer
    base_resp = client.get("/api/infrastructure/layers/e2e-trishuli-aug2026/baseline")
    assert base_resp.status_code == 200
    base_json = base_resp.json()
    assert base_json["type"] == "FeatureCollection"

    # GeoJSON Download
    dl_geojson = client.get("/api/infrastructure/download/e2e-trishuli-aug2026/geojson")
    assert dl_geojson.status_code == 200
    assert "application/geo+json" in dl_geojson.headers.get("content-type", "")

    # Summary Download
    dl_summary = client.get("/api/infrastructure/download/e2e-trishuli-aug2026/summary")
    assert dl_summary.status_code == 200
    assert "application/json" in dl_summary.headers.get("content-type", "")


def test_api_nonexistent_analysis_returns_404():
    """Verifies that requesting a nonexistent analysis returns 404."""
    resp = client.post("/api/infrastructure/analyze", json={
        "analysis_id": "nonexistent-analysis-id-xyz"
    })
    assert resp.status_code == 404

    resp_status = client.get("/api/infrastructure/status/nonexistent-analysis-id-xyz")
    assert resp_status.status_code == 404
