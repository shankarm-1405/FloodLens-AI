"""
Unit tests for configuration loader and defaults.
"""

from app.config import Settings


def test_default_settings():
    settings = Settings()
    assert isinstance(settings.DEMO_MODE, bool)
    assert settings.BACKEND_PORT == 8000
    assert settings.FRONTEND_PORT == 5173
    assert len(settings.DEFAULT_AOI_BBOX) == 4
    # Check default AOI is around Trishuli (approx 85.05 - 85.25 lon, 27.75 - 27.95 lat)
    min_lon, min_lat, max_lon, max_lat = settings.DEFAULT_AOI_BBOX
    assert 84.0 <= min_lon <= 86.0
    assert 26.0 <= min_lat <= 29.0
    assert settings.OSM_SNAPSHOT_DATE == "2026-07-27"
