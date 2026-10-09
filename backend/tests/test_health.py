"""
Unit tests for system health and metadata API endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "FloodLens AI"
    assert "version" in data
    assert "health_check" in data


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "geospatial_stack" in data
    assert "rasterio" in data["geospatial_stack"]
    assert "shapely" in data["geospatial_stack"]
    assert "geopandas" in data["geospatial_stack"]
    assert "networkx" in data["geospatial_stack"]
    assert data["geospatial_stack"]["rasterio"]["available"] is True
    assert data["geospatial_stack"]["shapely"]["available"] is True
    assert data["geospatial_stack"]["geopandas"]["available"] is True
    assert data["geospatial_stack"]["networkx"]["available"] is True
    assert "study_case" in data
    assert data["study_case"]["region"] == "Trishuli Corridor, Nepal"


def test_version_and_attributions():
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "FloodLens AI"
    assert "attributions" in data
    # Verify mandatory attribution statements from project requirements
    attributions_str = " ".join(data["attributions"])
    assert "Contains modified Copernicus Sentinel data 2026." in attributions_str
    assert "Produced using Copernicus WorldDEM-30" in attributions_str
    assert "© OpenStreetMap contributors." in attributions_str


def test_config_status_does_not_leak_secrets():
    response = client.get("/api/config-status")
    assert response.status_code == 200
    data = response.json()
    # Confirm secret credentials are not exposed
    assert "CDSE_PASSWORD" not in data
    assert "CDSE_CLIENT_SECRET" not in data
    assert "GEMINI_API_KEY" not in data
    assert "OPENAI_API_KEY" not in data
    assert "cdse_configured" in data
    assert "osm_snapshot_date" in data
    assert data["osm_snapshot_date"] == "2026-07-27"
