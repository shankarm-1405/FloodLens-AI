"""
End-to-End Multimodal Integration Test:
Verifies the complete 10-step disaster intelligence pipeline:
1. Search Sentinel-1 & Sentinel-2 acquisitions.
2. Check download credentials and product availability.
3. Attempt real-data processing without local files (verifies strict 422 rejection).
4. Execute flood analysis in designated demo mode.
5. Execute infrastructure exposure with historical baseline.
6. Execute settlement road disconnection graph model.
7. Generate English grounded situation report.
8. Generate Nepali grounded situation report.
9. Export reports to Markdown and PDF.
10. Download all output GeoJSON spatial layers.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_e2e_workflow():
    # 1. Search Sentinel-1 & Sentinel-2 acquisitions
    search_payload = {
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "event_date": "2026-08-04",
        "window_days": 15,
        "include_optical": True,
        "force_live": False
    }
    resp = client.post("/api/satellite/search", json=search_payload)
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    search_data = resp.json()
    assert len(search_data["sentinel1"]["compatible_pairs"]) > 0
    assert search_data["sentinel2"]["total_found"] > 0
    best_pair = search_data["sentinel1"]["best_compatible_pair"]
    assert best_pair is not None

    # 2. Check download credentials and product availability
    cred_resp = client.get("/api/satellite/credentials-status")
    assert cred_resp.status_code == 200

    dl_resp = client.post(f"/api/satellite/download-check?product_id={best_pair['post_event_scene']['id']}")
    assert dl_resp.status_code == 200

    # 3. Attempt real-data processing without files (Must fail cleanly with 422)
    real_attempt_payload = {
        "analysis_id": "test-e2e-missing-files",
        "pre_scene": best_pair["pre_event_scene"],
        "post_scene": best_pair["post_event_scene"],
        "is_demo": False
    }
    fail_resp = client.post("/api/flood/analyze", json=real_attempt_payload)
    assert fail_resp.status_code == 422, f"Expected 422, got {fail_resp.status_code}: {fail_resp.text}"

    # 4. Generate flood analysis outputs in demo mode
    analysis_id = "test-e2e-pipeline-01"
    analyze_payload = {
        "analysis_id": analysis_id,
        "pre_scene": best_pair["pre_event_scene"],
        "post_scene": best_pair["post_event_scene"],
        "bbox": [85.05, 27.75, 85.25, 27.95],
        "is_demo": True
    }
    analyze_resp = client.post("/api/flood/analyze", json=analyze_payload)
    assert analyze_resp.status_code == 200, f"Analyze failed: {analyze_resp.text}"
    flood_meta = analyze_resp.json()
    assert flood_meta["analysis_id"] == analysis_id
    assert flood_meta["area_statistics"]["candidate_flood_area_sqkm"] > 0

    # 5. Run infrastructure exposure
    infra_payload = {
        "analysis_id": analysis_id,
        "osm_source": "historical",
        "allow_fallback_fixture": True
    }
    infra_resp = client.post("/api/infrastructure/analyze", json=infra_payload)
    assert infra_resp.status_code == 200, f"Infra analyze failed: {infra_resp.text}"
    infra_data = infra_resp.json()
    assert infra_data["exposed_buildings_count"] == 3
    assert infra_data["provenance"] == "SYNTHETIC_TEST_FIXTURE"

    # 6. Run settlement connectivity
    conn_payload = {
        "analysis_id": analysis_id,
        "closure_method": "complete_severance",
        "snapping_tolerance_m": 50.0,
        "allow_fallback_fixture": True
    }
    conn_resp = client.post("/api/connectivity/analyze", json=conn_payload)
    assert conn_resp.status_code == 200, f"Conn analyze failed: {conn_resp.text}"
    conn_data = conn_resp.json()
    assert conn_data["summary_counts"]["newly_disconnected"] == 2
    assert conn_data["provenance"] == "SYNTHETIC_TEST_FIXTURE"

    # 7. Generate English situation report
    report_gen_resp = client.post("/api/report/generate", json={"analysis_id": analysis_id, "language": "en"})
    assert report_gen_resp.status_code == 200, f"Report gen failed: {report_gen_resp.text}"
    report_en = report_gen_resp.json()
    assert report_en["report_id"] == f"SITREP-{analysis_id}-EN"
    assert report_en["provenance"] == "SYNTHETIC_TEST_FIXTURE"

    # 8. Generate Nepali situation report
    report_gen_ne = client.post("/api/report/generate", json={"analysis_id": analysis_id, "language": "ne"})
    assert report_gen_ne.status_code == 200
    report_ne = report_gen_ne.json()
    assert report_ne["report_id"] == f"SITREP-{analysis_id}-NE"
    assert report_ne["language"] == "ne"

    # 9. Export both reports to Markdown and PDF
    md_en = client.get(f"/api/report/{analysis_id}/export/markdown?lang=en")
    assert md_en.status_code == 200
    assert len(md_en.content) > 500

    pdf_en = client.get(f"/api/report/{analysis_id}/export/pdf?lang=en")
    assert pdf_en.status_code == 200
    assert pdf_en.headers["content-type"] == "application/pdf"
    assert len(pdf_en.content) > 1000

    md_ne = client.get(f"/api/report/{analysis_id}/export/markdown?lang=ne")
    assert md_ne.status_code == 200
    assert len(md_ne.content) > 500

    pdf_ne = client.get(f"/api/report/{analysis_id}/export/pdf?lang=ne")
    assert pdf_ne.status_code == 200
    assert pdf_ne.headers["content-type"] == "application/pdf"
    assert len(pdf_ne.content) > 1000

    # 10. Download GeoJSON outputs
    flood_geojson = client.get(f"/api/flood/download/{analysis_id}/geojson")
    assert flood_geojson.status_code == 200

    infra_exposed = client.get(f"/api/infrastructure/layers/{analysis_id}/exposed")
    assert infra_exposed.status_code == 200

    infra_baseline = client.get(f"/api/infrastructure/layers/{analysis_id}/baseline")
    assert infra_baseline.status_code == 200

    conn_closed = client.get(f"/api/connectivity/layers/{analysis_id}/closed_roads")
    assert conn_closed.status_code == 200

    conn_routes = client.get(f"/api/connectivity/layers/{analysis_id}/routes")
    assert conn_routes.status_code == 200
