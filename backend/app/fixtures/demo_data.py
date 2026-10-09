"""
Offline demonstration fixtures for FloodLens AI.
Clearly marked and separated from live satellite pipelines.
"""

from typing import Dict, Any, List

DEMO_DISCLAIMER = "DEMONSTRATION DATA — NOT REAL FLOOD ANALYSIS"

DEMO_SENTINEL1_ACQUISITIONS: List[Dict[str, Any]] = [
    {
        "id": "demo-s1-pre-20260728",
        "name": "S1D_IW_GRDH_1SDV_20260728T001522_20260728T001547_004721_008FA1_DEMO.SAFE",
        "satellite": "Sentinel-1D",
        "instrument": "C-SAR",
        "product_type": "GRD",
        "acquisition_date": "2026-07-28T00:15:22.000Z",
        "orbit_pass": "DESCENDING",
        "relative_orbit": 121,
        "polarization": "VV&VH",
        "footprint_wkt": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))",
        "timing_relation": "PRE_EVENT",
        "compatibility_score": 1.0,
        "is_demo_fixture": True,
        "label": DEMO_DISCLAIMER
    },
    {
        "id": "demo-s1-post-20260805",
        "name": "S1D_IW_GRDH_1SDV_20260805T001520_20260805T001545_004825_009112_DEMO.SAFE",
        "satellite": "Sentinel-1D",
        "instrument": "C-SAR",
        "product_type": "GRD",
        "acquisition_date": "2026-08-05T00:15:20.000Z",
        "orbit_pass": "DESCENDING",
        "relative_orbit": 121,
        "polarization": "VV&VH",
        "footprint_wkt": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))",
        "timing_relation": "POST_EVENT",
        "compatibility_score": 1.0,
        "is_demo_fixture": True,
        "label": DEMO_DISCLAIMER
    },
    {
        "id": "demo-s1-suboptimal-20260803",
        "name": "S1D_IW_GRDH_1SDV_20260803T122142_20260803T122207_004790_009050_DEMO.SAFE",
        "satellite": "Sentinel-1D",
        "instrument": "C-SAR",
        "product_type": "GRD",
        "acquisition_date": "2026-08-03T12:21:42.000Z",
        "orbit_pass": "ASCENDING",
        "relative_orbit": 85,
        "polarization": "VV&VH",
        "footprint_wkt": "POLYGON((84.8 27.5, 85.5 27.5, 85.5 28.2, 84.8 28.2, 84.8 27.5))",
        "timing_relation": "PRE_EVENT",
        "compatibility_score": 0.4,
        "is_demo_fixture": True,
        "label": DEMO_DISCLAIMER
    }
]

DEMO_SENTINEL2_ACQUISITIONS: List[Dict[str, Any]] = [
    {
        "id": "demo-s2-20260806",
        "name": "S2B_MSIL2A_20260806T044809_N0510_R119_T45RVP_DEMO.SAFE",
        "satellite": "Sentinel-2B",
        "instrument": "MSI",
        "product_type": "MSIL2A",
        "acquisition_date": "2026-08-06T04:48:09.000Z",
        "cloud_cover_percentage": 68.4,
        "recommendation": "RESTRICTED (Cloud > 50% hinders optical NDWI cross-validation)",
        "is_demo_fixture": True,
        "label": DEMO_DISCLAIMER
    },
    {
        "id": "demo-s2-20260727",
        "name": "S2A_MSIL2A_20260727T044811_N0510_R119_T45RVP_DEMO.SAFE",
        "satellite": "Sentinel-2A",
        "instrument": "MSI",
        "product_type": "MSIL2A",
        "acquisition_date": "2026-07-27T04:48:11.000Z",
        "cloud_cover_percentage": 18.2,
        "recommendation": "OPTIMAL (Cloud < 20% suitable for baseline NDWI water mapping)",
        "is_demo_fixture": True,
        "label": DEMO_DISCLAIMER
    }
]
