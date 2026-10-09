"""
API integration tests for satellite discovery endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_credentials_status_endpoint():
    response = client.get("/api/satellite/credentials-status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "auth_method" in data
    assert "guidance" in data
    assert "dataspace.copernicus.eu" in data["guidance"]["registration_portal"]


def test_search_satellite_demo_mode():
    payload = {
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "event_date": "2026-08-04",
        "window_days": 15,
        "include_optical": True,
        "force_live": False
    }
    response = client.post("/api/satellite/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "DEMONSTRATION_MODE"
    assert data["is_demo_fixture"] is True
    assert "DEMONSTRATION DATA" in data["disclaimer"]
    assert "sentinel1" in data
    assert data["sentinel1"]["total_found"] >= 2
    assert "best_compatible_pair" in data["sentinel1"]
    assert data["sentinel1"]["best_compatible_pair"]["compatibility_level"] == "OPTIMAL"
    assert "sentinel2" in data


def test_search_satellite_invalid_coordinates():
    payload = {
        "bbox": [195.0, 27.75, 85.25, 27.95],
        "event_date": "2026-08-04"
    }
    response = client.post("/api/satellite/search", json=payload)
    assert response.status_code == 400
    assert "Longitudes must be between" in response.json()["detail"]


def test_search_satellite_invalid_date():
    payload = {
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "event_date": "not-valid-date"
    }
    response = client.post("/api/satellite/search", json=payload)
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


def test_download_check_endpoint():
    response = client.post("/api/satellite/download-check?product_id=5b119648-53e0-4a8a-a7a0-f79d20fa7bf4")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["downloaded"] in (True, False)
