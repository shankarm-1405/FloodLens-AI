"""
Unit tests for CopernicusClient using mocked catalog responses.
Verifies OData parsing, error handling, and download preparation.
"""

from unittest.mock import patch, MagicMock
from app.core.copernicus import CopernicusClient


@patch("requests.get")
def test_search_sentinel1_mocked(mock_get):
    client = CopernicusClient()

    # Mock OData response payload
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "value": [
            {
                "Id": "prod-1",
                "Name": "S1D_IW_GRDH_1SDV_20260728T001522_COG.SAFE",
                "ContentDate": {"Start": "2026-07-28T00:15:22.000Z"},
                "Attributes": [
                    {"Name": "orbitDirection", "Value": "DESCENDING"},
                    {"Name": "relativeOrbitNumber", "Value": 121},
                    {"Name": "polarisationChannels", "Value": "VV&VH"}
                ],
                "Footprint": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))"
            },
            {
                "Id": "prod-2",
                "Name": "S1D_IW_GRDH_1SDV_20260805T001520_COG.SAFE",
                "ContentDate": {"Start": "2026-08-05T00:15:20.000Z"},
                "Attributes": [
                    {"Name": "orbitDirection", "Value": "DESCENDING"},
                    {"Name": "relativeOrbitNumber", "Value": 121},
                    {"Name": "polarisationChannels", "Value": "VV&VH"}
                ],
                "Footprint": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))"
            }
        ]
    }
    mock_get.return_value = mock_response

    results = client.search_sentinel1_acquisitions(
        bbox=[85.05, 27.75, 85.25, 27.95],
        event_date_str="2026-08-04",
        window_days=10
    )

    assert results["total_found"] == 2
    assert results["pre_event_count"] == 1
    assert results["post_event_count"] == 1
    assert len(results["compatible_pairs"]) == 1

    best_pair = results["best_compatible_pair"]
    assert best_pair is not None
    assert best_pair["compatibility_level"] == "OPTIMAL"
    assert best_pair["pre_event_scene"]["id"] == "prod-1"
    assert best_pair["post_event_scene"]["id"] == "prod-2"


@patch("requests.get")
def test_search_sentinel2_mocked(mock_get):
    client = CopernicusClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "value": [
            {
                "Id": "s2-prod-1",
                "Name": "S2B_MSIL2A_20260806T044809.SAFE",
                "ContentDate": {"Start": "2026-08-06T04:48:09.000Z"},
                "Attributes": [
                    {"Name": "cloudCover", "Value": 68.4}
                ],
                "Footprint": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))"
            }
        ]
    }
    mock_get.return_value = mock_response

    results = client.search_sentinel2_acquisitions(
        bbox=[85.05, 27.75, 85.25, 27.95],
        event_date_str="2026-08-04",
        window_days=5
    )

    assert results["total_found"] == 1
    assert results["usable_for_ndwi_count"] == 0
    assert results["acquisitions"][0]["cloud_cover_percentage"] == 68.4


def test_prepare_download_credentials_required():
    client = CopernicusClient()
    # When no token is configured, should report CREDENTIALS_REQUIRED
    with patch.object(client, "get_auth_token", return_value=None):
        status = client.prepare_download("dummy-uuid")
        assert status["status"] == "CREDENTIALS_REQUIRED"
        assert status["downloaded"] is False
        assert "setup_guide" in status
