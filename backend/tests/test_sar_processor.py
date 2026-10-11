"""
Unit tests for SAR processing engine:
Grid alignment, incompatible pairs, log-ratio calculation, speckle filtering,
slope masking, nodata handling, area statistics, GeoTIFF, and GeoJSON outputs.
Using synthetic rasters clearly designated as TEST FIXTURES.
"""

import json
import zipfile
import pytest
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path

from app.core.sar_processor import (
    sar_processor,
    SARProcessor,
    SARProcessingParameters,
    ImageGridMismatchError,
    IncompatiblePairError,
    MissingMeasurementFilesError
)
from app.core.copernicus import (
    copernicus_client,
    PathTraversalError,
    ArchiveIntegrityError
)


def test_image_grid_mismatch_error():
    pre_arr = np.zeros((100, 100), dtype=float)
    post_arr = np.zeros((80, 100), dtype=float)

    with pytest.raises(ImageGridMismatchError, match="grid dimensions do not match"):
        SARProcessor.compute_log_ratio(pre_arr, post_arr)


def test_incompatible_pair_rejection():
    pre_scene = {
        "id": "s1-pre-asc",
        "acquisition_date": "2026-07-28T00:00:00Z",
        "orbit_pass": "ASCENDING",
        "relative_orbit": 85
    }
    post_scene = {
        "id": "s1-post-desc",
        "acquisition_date": "2026-08-05T00:00:00Z",
        "orbit_pass": "DESCENDING",
        "relative_orbit": 121
    }
    params = SARProcessingParameters()

    with pytest.raises(IncompatiblePairError, match="Incompatible orbit passes"):
        SARProcessor.execute_flood_analysis(
            analysis_id="test-incompatible",
            pre_scene=pre_scene,
            post_scene=post_scene,
            bbox=[85.05, 27.75, 85.25, 27.95],
            params=params,
            is_demo_mode=True
        )


def test_log_ratio_calculation():
    pre = np.array([[-10.0, -12.0], [-8.0, np.nan]])
    post = np.array([[-15.0, -12.0], [-14.0, -10.0]])

    diff = SARProcessor.compute_log_ratio(pre, post)
    assert diff[0, 0] == -5.0  # -15 - (-10) = -5 dB drop
    assert diff[0, 1] == 0.0   # No change
    assert diff[1, 0] == -6.0  # -14 - (-8) = -6 dB drop
    assert np.isnan(diff[1, 1])


def test_speckle_median_filter():
    # Array with an isolated speckle noise spike
    noisy = np.full((5, 5), -10.0)
    noisy[2, 2] = 5.0  # Isolated radar speckle noise spike
    filtered = SARProcessor.apply_speckle_filter(noisy, kernel_size=3)
    assert filtered[2, 2] == -10.0  # Filtered out by median


def test_slope_calculation_and_shadow_masking():
    # Flat terrain: slope ~ 0 deg
    flat_dem = np.full((10, 10), 500.0, dtype=float)
    flat_slope = SARProcessor.compute_slope_from_dem(flat_dem, cell_size_m=30.0)
    assert np.all(flat_slope == 0.0)

    # Steep mountain slope: 600m rise over 300m (~ 63.4 degrees)
    steep_dem = np.zeros((10, 10), dtype=float)
    for r in range(10):
        steep_dem[r, :] = r * 60.0  # 60m drop per 30m cell
    steep_slope = SARProcessor.compute_slope_from_dem(steep_dem, cell_size_m=30.0)
    assert np.all(steep_slope[1:-1, :] > 15.0)


def test_nodata_handling():
    pre_arr = np.full((10, 10), -10.0)
    post_arr = np.full((10, 10), -15.0)
    # Set corner to NaN
    pre_arr[0, 0] = np.nan
    post_arr[9, 9] = np.nan

    params = SARProcessingParameters()
    classification, _, counts = SARProcessor.classify_inundation(
        pre_db=pre_arr,
        post_db=post_arr,
        dem_elevation=None,
        params=params
    )

    assert classification[0, 0] == SARProcessor.CLASS_NODATA
    assert classification[9, 9] == SARProcessor.CLASS_NODATA
    assert counts["nodata_pixels"] == 2


def test_threshold_sensitivity():
    # Synthetic scene: test stricter vs sensitive threshold
    pre, post, dem, _ = SARProcessor.create_synthetic_test_scene(rows=50, cols=50)

    strict_params = SARProcessingParameters(threshold_db=-4.5)
    class_strict, _, counts_strict = SARProcessor.classify_inundation(pre, post, dem, strict_params)

    sensitive_params = SARProcessingParameters(threshold_db=-2.0)
    class_sens, _, counts_sens = SARProcessor.classify_inundation(pre, post, dem, sensitive_params)

    # Sensitive threshold should detect at least as many or more flood pixels
    assert counts_sens["candidate_flood_pixels"] >= counts_strict["candidate_flood_pixels"]


def test_area_calculation_consistency():
    counts = {
        "total_pixels": 10000,
        "valid_pixels": 9500,
        "nodata_pixels": 500,
        "unaffected_land_pixels": 8000,
        "candidate_flood_pixels": 1000,
        "permanent_water_pixels": 300,
        "terrain_shadow_pixels": 200,
    }
    # 10m x 10m = 100 m^2 per pixel
    pixel_area = 100.0
    stats = SARProcessor.calculate_area_statistics(counts, pixel_area)

    # 1000 pixels * 100 m^2 = 100,000 m^2 = 0.100 km^2
    assert stats["candidate_flood_area_sqkm"] == 0.1
    # 300 pixels * 100 m^2 = 0.030 km^2
    assert stats["permanent_water_area_sqkm"] == 0.03
    assert stats["valid_coverage_ratio"] == 0.95


def test_geotiff_georeferencing_and_geojson_outputs(tmp_path):
    pre, post, dem, transform = SARProcessor.create_synthetic_test_scene(rows=40, cols=40)
    params = SARProcessingParameters()
    classification, _, _ = SARProcessor.classify_inundation(pre, post, dem, params)

    # Test GeoTIFF
    tif_path = tmp_path / "test_flood.tif"
    SARProcessor.write_geotiff(tif_path, classification, transform, "EPSG:4326")
    assert tif_path.exists()

    with rasterio.open(tif_path) as src:
        assert src.count == 1
        assert src.shape == (40, 40)
        assert src.crs.to_string() == "EPSG:4326"
        assert src.nodata == 255
        read_data = src.read(1)
        assert np.array_equal(read_data, classification)

    # Test GeoJSON
    geojson = SARProcessor.vectorize_to_geojson(classification, transform, "EPSG:4326", min_polygon_pixels=3)
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) > 0
    first_feat = geojson["features"][0]
    assert first_feat["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert first_feat["properties"]["class"] == "CANDIDATE_FLOOD"


def test_missing_measurement_files_error():
    with pytest.raises(MissingMeasurementFilesError, match="not found"):
        SARProcessor.find_measurement_files("non_existent_safe_product_123")

    # In non-demo mode, missing measurements on disk should raise MissingMeasurementFilesError
    pre_scene = {"id": "s1-nonexistent-pre", "orbit_pass": "DESCENDING"}
    post_scene = {"id": "s1-nonexistent-post", "orbit_pass": "DESCENDING"}
    with pytest.raises(MissingMeasurementFilesError, match="Missing real measurement files on disk"):
        SARProcessor.execute_flood_analysis(
            analysis_id="test-missing-files",
            pre_scene=pre_scene,
            post_scene=post_scene,
            bbox=[85.05, 27.75, 85.25, 27.95],
            params=SARProcessingParameters(),
            is_demo_mode=False
        )


def test_calibrate_dn_to_backscatter_db():
    dn_arr = np.array([[300.0, 30.0], [0.0, np.nan]], dtype=np.float32)
    db_arr = SARProcessor.calibrate_dn_to_backscatter_db(dn_arr, calibration_constant=300.0)
    # 20 * log10(300) - 20 * log10(300) = 0.0 dB
    assert pytest.approx(db_arr[0, 0], abs=1e-4) == 0.0
    # 20 * log10(30) - 20 * log10(300) = -20.0 dB
    assert pytest.approx(db_arr[0, 1], abs=1e-4) == -20.0
    # DN == 0 is nodata
    assert np.isnan(db_arr[1, 0])
    # DN == nan is nodata
    assert np.isnan(db_arr[1, 1])


def test_reproject_to_grid():
    from rasterio.transform import from_bounds
    src_data = np.full((10, 10), -12.0, dtype=np.float32)
    src_tf = from_bounds(85.0, 27.0, 85.5, 27.5, 10, 10)
    dst_tf = from_bounds(85.0, 27.0, 85.5, 27.5, 20, 20)

    reprojected = SARProcessor.reproject_to_grid(
        source_data=src_data,
        source_transform=src_tf,
        source_crs="EPSG:4326",
        target_shape=(20, 20),
        target_transform=dst_tf,
        target_crs="EPSG:4326"
    )
    assert reprojected.shape == (20, 20)
    assert pytest.approx(reprojected[10, 10], abs=0.1) == -12.0


def test_safe_extract_zip_path_traversal_prevention(tmp_path):
    # Construct a malicious zip with path traversal attempt: ../malicious.txt
    malicious_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../malicious.txt", "exploit payload")

    target_dir = tmp_path / "safe_extract_target"
    with pytest.raises(PathTraversalError, match="Illegal path traversal detected"):
        copernicus_client.safe_extract_zip(malicious_zip, target_dir)


def test_archive_integrity_check(tmp_path):
    # Corrupt zip file
    corrupt_file = tmp_path / "corrupt.zip"
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_REAL_ZIP_HEADER_CORRUPTED_BYTES")

    target_dir = tmp_path / "extract_dest"
    with pytest.raises(ArchiveIntegrityError, match="Invalid or corrupted zip"):
        copernicus_client.safe_extract_zip(corrupt_file, target_dir)


def test_geodesic_vs_projected_pixel_area():
    from rasterio.transform import Affine
    # 1. Projected UTM CRS: 10m x 10m pixel = 100 m^2
    utm_transform = Affine(10.0, 0.0, 300000.0, 0.0, -10.0, 3000000.0)
    utm_area = SARProcessor.calculate_pixel_area_sqm(utm_transform, "EPSG:32645", center_lat=27.85)
    assert pytest.approx(utm_area, abs=1e-3) == 100.0

    # 2. Geographic WGS84 CRS: 0.0001 deg (~11m lat, ~9.8m lon)
    geo_transform = Affine(0.0001, 0.0, 85.05, 0.0, -0.0001, 27.95)
    geo_area = SARProcessor.calculate_pixel_area_sqm(geo_transform, "EPSG:4326", center_lat=27.85)
    # Area should be strictly positive and between 105 and 115 m^2
    assert 105.0 < geo_area < 115.0


def test_parse_calibration_xml_synthetic(tmp_path):
    # Create synthetic Sentinel-1 calibration XML fixture
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <calibration>
      <calibrationVectorList count="1">
        <calibrationVector>
          <line>0</line>
          <pixel>0</pixel>
          <sigmaNought>312.4 314.1 310.8 315.0</sigmaNought>
        </calibrationVector>
      </calibrationVectorList>
    </calibration>"""
    xml_file = tmp_path / "calibration-s1d-iw-grd-vv.xml"
    xml_file.write_text(xml_content, encoding="utf-8")

    calib_val = SARProcessor.parse_calibration_xml(xml_file)
    assert calib_val is not None
    assert pytest.approx(calib_val, abs=1.0) == 313.0

    # Calibrate with XML path
    dn_arr = np.array([[313.0]], dtype=np.float32)
    db = SARProcessor.calibrate_dn_to_backscatter_db(dn_arr, calibration_xml_path=xml_file)
    # 20 * log10(313) - 20 * log10(313) ~ 0 dB
    assert pytest.approx(db[0, 0], abs=0.1) == 0.0


def test_find_measurement_files_from_zip_archive(tmp_path):
    # Create a synthetic Sentinel-1 SAFE directory structure inside a zip
    product_name = "S1D_IW_GRDH_TEST_PRODUCT"
    zip_path = tmp_path / f"{product_name}.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{product_name}.SAFE/measurement/s1d-iw-grd-vv-test.tiff", b"RIFF_FAKE_TIFF_HEADER")
        zf.writestr(f"{product_name}.SAFE/annotation/calibration/calibration-s1d-iw-grd-vv.xml", b"<calibration/>")

    # Pass the zip path to find_measurement_files
    meas_tiff, calib_xml = SARProcessor.find_measurement_files(zip_path, polarization="vv")
    assert meas_tiff.exists()
    assert "vv" in meas_tiff.name
    assert calib_xml is not None
    assert calib_xml.exists()

