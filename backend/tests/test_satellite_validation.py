"""
Unit tests for satellite coordinate validation, date parsing,
compatibility evaluation, and cloud cover classification.
"""

import pytest
from datetime import datetime, timezone
from app.core.copernicus import (
    CopernicusClient,
    InvalidCoordinatesError,
    InvalidDateError
)


def test_valid_aoi_bbox():
    valid_box = [85.05, 27.75, 85.25, 27.95]
    coords = CopernicusClient.validate_aoi_bbox(valid_box)
    assert coords["min_lon"] == 85.05
    assert coords["min_lat"] == 27.75
    assert coords["max_lon"] == 85.25
    assert coords["max_lat"] == 27.95


def test_invalid_aoi_bbox_length():
    with pytest.raises(InvalidCoordinatesError, match="4-element list"):
        CopernicusClient.validate_aoi_bbox([85.05, 27.75, 85.25])


def test_invalid_aoi_bbox_coordinates_range():
    with pytest.raises(InvalidCoordinatesError, match="Longitudes must be between"):
        CopernicusClient.validate_aoi_bbox([195.0, 27.0, 196.0, 28.0])

    with pytest.raises(InvalidCoordinatesError, match="Latitudes must be between"):
        CopernicusClient.validate_aoi_bbox([85.0, -95.0, 86.0, 28.0])


def test_invalid_aoi_bbox_inverted_min_max():
    with pytest.raises(InvalidCoordinatesError, match="strictly less"):
        CopernicusClient.validate_aoi_bbox([86.0, 27.0, 85.0, 28.0])

    with pytest.raises(InvalidCoordinatesError, match="strictly less"):
        CopernicusClient.validate_aoi_bbox([85.0, 29.0, 86.0, 28.0])


def test_valid_event_date_parsing():
    dt = CopernicusClient.validate_event_date("2026-08-04")
    assert dt.year == 2026
    assert dt.month == 8
    assert dt.day == 4


def test_invalid_event_date():
    with pytest.raises(InvalidDateError, match="Invalid date format"):
        CopernicusClient.validate_event_date("not-a-date")

    with pytest.raises(InvalidDateError, match="operational Sentinel"):
        CopernicusClient.validate_event_date("1995-05-10")


def test_s1_pair_compatibility_math():
    client = CopernicusClient()

    pre_asc_track85 = {
        "id": "s1-pre",
        "name": "S1_PRE",
        "acquisition_date": "2026-07-28T00:00:00Z",
        "orbit_pass": "ASCENDING",
        "relative_orbit": 85,
        "polarization": "VV&VH",
        "timing_relation": "PRE_EVENT",
        "days_from_event": 7.0
    }

    post_asc_track85 = {
        "id": "s1-post-opt",
        "name": "S1_POST_OPT",
        "acquisition_date": "2026-08-05T00:00:00Z",
        "orbit_pass": "ASCENDING",
        "relative_orbit": 85,
        "polarization": "VV&VH",
        "timing_relation": "POST_EVENT",
        "days_from_event": 1.0
    }

    post_desc_track121 = {
        "id": "s1-post-incomp",
        "name": "S1_POST_INCOMP",
        "acquisition_date": "2026-08-05T00:00:00Z",
        "orbit_pass": "DESCENDING",
        "relative_orbit": 121,
        "polarization": "VV&VH",
        "timing_relation": "POST_EVENT",
        "days_from_event": 1.0
    }

    pairs = client._evaluate_s1_pairs([pre_asc_track85], [post_asc_track85, post_desc_track121])
    assert len(pairs) == 2

    best = pairs[0]
    assert best["post_event_scene"]["id"] == "s1-post-opt"
    assert best["compatibility_level"] == "OPTIMAL"
    assert best["compatibility_score"] >= 0.85

    worst = pairs[1]
    assert worst["post_event_scene"]["id"] == "s1-post-incomp"
    assert worst["compatibility_level"] == "INCOMPATIBLE"
    assert worst["compatibility_score"] < 0.50
    assert "Mismatched orbit direction" in " ".join(worst["detailed_criteria"])


def test_s2_product_cloud_parsing():
    client = CopernicusClient()

    clear_scene = {
        "Name": "S2A_MSIL2A_20260727",
        "Id": "s2-clear",
        "ContentDate": {"Start": "2026-07-27T04:00:00Z"},
        "Attributes": [{"Name": "cloudCover", "Value": 12.5}]
    }
    parsed_clear = client._parse_s2_product(clear_scene)
    assert parsed_clear is not None
    assert parsed_clear["cloud_cover_percentage"] == 12.5
    assert "OPTIMAL" in parsed_clear["recommendation"]

    cloudy_scene = {
        "Name": "S2B_MSIL2A_20260806",
        "Id": "s2-cloudy",
        "ContentDate": {"Start": "2026-08-06T04:00:00Z"},
        "Attributes": [{"Name": "cloudCover", "Value": 78.2}]
    }
    parsed_cloudy = client._parse_s2_product(cloudy_scene)
    assert parsed_cloudy is not None
    assert parsed_cloudy["cloud_cover_percentage"] == 78.2
    assert "RESTRICTED" in parsed_cloudy["recommendation"]
