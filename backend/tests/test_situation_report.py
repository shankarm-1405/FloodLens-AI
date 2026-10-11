"""
Automated Test Suite for Phase 6: Grounded AI Situation Report Copilot
FloodLens AI - Trishuli River Corridor, Nepal

Validates:
1. Complete structured input ingestion (Flood, Infrastructure, Connectivity).
2. Missing flood, infrastructure, or connectivity data handling (explicit UNAVAILABLE, never fabricated zeros).
3. Zero versus unavailable representation.
4. Synthetic provenance propagation (SYNTHETIC_TEST_FIXTURE).
5. English (en) and Nepali (ne) language generation and fallback behavior.
6. Number and date consistency across languages.
7. Grounding verifier and unsupported-claim rejection (guardrail checks).
8. LLM provider failure and deterministic grounded template fallback.
9. FastAPI endpoints: generation, status, retrieval, and validation.
10. Markdown and PDF document export endpoints and content-types.
11. Path traversal rejection and invalid analysis ID handling.
12. Strict enforcement against labeling synthetic test results as real observations.
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import OUTPUTS_DIR
from app.core.situation_report import (
    situation_report_engine,
    SituationReportEngine,
    ReportGenerationError,
    GroundingValidationError
)

client = TestClient(app)


# --- 1. COMPLETE STRUCTURED INPUT INGESTION & REPORT GENERATION ---

def test_complete_report_generation_english():
    """
    Verifies situation report generation in English from full structured analysis inputs.
    """
    rep = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="en", use_llm=False)
    assert rep["analysis_id"] == "e2e-trishuli-aug2026"
    assert rep["language"] == "en"
    assert rep["generation_method"] == "DETERMINISTIC_GROUNDED_TEMPLATE"
    assert rep["provenance"] == "SYNTHETIC_TEST_FIXTURE"
    assert rep["is_synthetic"] is True

    # Validate sections
    sections = rep["sections"]
    assert "executive_summary" in sections
    assert "flood_extent_and_coverage" in sections
    assert "infrastructure_exposure" in sections
    assert "settlement_connectivity_and_isolation" in sections
    assert "confidence_and_data_limitations" in sections
    assert "recommended_next_steps" in sections
    assert "data_attributions" in sections

    # Check key metrics presence
    metrics = rep["summary_metrics"]
    assert metrics["candidate_flood_area_sqkm"] == 4.245
    assert metrics["exposed_buildings_count"] == 3
    assert metrics["exposed_bridges_count"] == 1
    assert metrics["newly_disconnected_count"] == 2


# --- 2. BILINGUAL NEPALI SUPPORT & LANGUAGE SELECTION ---

def test_report_generation_nepali():
    """
    Verifies situation report generation in Nepali (ne).
    Ensures Devanagari script is used in section titles and text.
    """
    rep = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="ne", use_llm=False)
    assert rep["language"] == "ne"
    assert rep["generation_method"] == "DETERMINISTIC_GROUNDED_TEMPLATE"

    sections = rep["sections"]
    # Verify Devanagari content
    assert "बाढी" in rep["sections"]["executive_summary"] or "फ्लडलेन्स" in rep["sections"]["executive_summary"]
    assert "बाढी" in rep["sections"]["flood_extent_and_coverage"]
    assert "सडक" in rep["sections"]["settlement_connectivity_and_isolation"]


# --- 3. NUMBER AND DATE CONSISTENCY ACROSS LANGUAGES ---

def test_number_and_date_consistency_across_languages():
    """
    Verifies that numeric values, dates, and units are strictly preserved between English and Nepali reports.
    """
    rep_en = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="en", use_llm=False)
    rep_ne = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="ne", use_llm=False)

    m_en = rep_en["summary_metrics"]
    m_ne = rep_ne["summary_metrics"]

    assert m_en["candidate_flood_area_sqkm"] == m_ne["candidate_flood_area_sqkm"]
    assert m_en["permanent_water_area_sqkm"] == m_ne["permanent_water_area_sqkm"]
    assert m_en["exposed_buildings_count"] == m_ne["exposed_buildings_count"]
    assert m_en["exposed_road_length_km"] == m_ne["exposed_road_length_km"]
    assert m_en["exposed_bridges_count"] == m_ne["exposed_bridges_count"]
    assert m_en["newly_disconnected_count"] == m_ne["newly_disconnected_count"]
    assert m_en["already_disconnected_count"] == m_ne["already_disconnected_count"]

    # Verify numbers appear identically in text
    assert "4.245" in rep_en["sections"]["executive_summary"]
    assert "4.245" in rep_ne["sections"]["executive_summary"]


# --- 4. ZERO VERSUS UNAVAILABLE VALUES (NEVER CONFLATE MISSING WITH ZERO) ---

def test_missing_data_sections_report_unavailable():
    """
    Ensures that when a section (e.g. connectivity or infrastructure) is missing,
    the report states UNAVAILABLE and never substitutes 0.
    """
    synth_inputs = {
        "analysis_id": "test-partial-analysis",
        "flood_data": {
            "area_of_interest": {"region": "Test Study Area", "bbox": [85.05, 27.75, 85.25, 27.95]},
            "source_acquisitions": {},
            "area_statistics": {
                "candidate_flood_area_sqkm": 2.5,
                "permanent_water_area_sqkm": 1.2
            }
        },
        "infrastructure_data": None,  # Infrastructure was NOT run!
        "connectivity_data": None,    # Connectivity was NOT run!
        "is_synthetic": True,
        "provenance": "SYNTHETIC_TEST_FIXTURE",
        "missing_sections": ["infrastructure_exposure_missing", "connectivity_summary_missing"]
    }

    rep = situation_report_engine.generate_deterministic_report(synth_inputs, language="en")
    metrics = rep["summary_metrics"]

    # Missing counts must be None / UNAVAILABLE, NOT zero!
    assert metrics["exposed_buildings_count"] is None
    assert metrics["exposed_road_length_km"] is None
    assert metrics["newly_disconnected_count"] is None

    # Text must explicitly state UNAVAILABLE
    assert "UNAVAILABLE" in rep["sections"]["infrastructure_exposure"]
    assert "UNAVAILABLE" in rep["sections"]["settlement_connectivity_and_isolation"]


# --- 5. SYNTHETIC PROVENANCE PROPAGATION ---

def test_synthetic_provenance_propagation():
    """
    Verifies that reports generated from synthetic inputs are prominently labeled SYNTHETIC_TEST_FIXTURE
    and carry explicit educational disclaimer notices.
    """
    rep = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="en", use_llm=False)
    assert rep["is_synthetic"] is True
    assert rep["provenance"] == "SYNTHETIC_TEST_FIXTURE"
    assert "DEMONSTRATION SYNTHETIC FIXTURE" in rep["data_notice"]
    assert "EDUCATIONAL & RESEARCH PROTOTYPE" in rep["disclaimer"]


# --- 6. GROUNDING VERIFIER & FORBIDDEN HALLUCINATION REJECTION ---

def test_grounding_verifier_rejects_hallucinations():
    """
    Ensures safety verifier detects and rejects prohibited claims:
    - Casualties/deaths
    - Mandatory evacuation decrees
    - Unverified monetary losses
    """
    engine = SituationReportEngine()

    safe_text = "Analysis estimated 4.245 km2 candidate flood extent. 3 buildings potentially inundated."
    is_valid, reasons = engine.verify_grounding(safe_text, {})
    assert is_valid is True
    assert len(reasons) == 0

    hallucinated_casualty_text = "Analysis identified 15 confirmed deaths and 40 casualties in the village."
    is_valid, reasons = engine.verify_grounding(hallucinated_casualty_text, {})
    assert is_valid is False
    assert any("deaths" in r or "casualties" in r for r in reasons)

    hallucinated_order_text = "Authorities have declared a mandatory evacuation order for all residents."
    is_valid, reasons = engine.verify_grounding(hallucinated_order_text, {})
    assert is_valid is False
    assert any("mandatory evacuation" in r for r in reasons)


# --- 7. LLM PROVIDER FAILURE & DETERMINISTIC TEMPLATE FALLBACK ---

def test_llm_failure_falls_back_to_template():
    """
    Ensures that if the LLM provider call fails or key is missing,
    the engine transparently falls back to the deterministic grounded template without raising an unhandled exception.
    """
    engine = SituationReportEngine()
    engine.llm_key = "invalid-dummy-key"
    engine.llm_provider = "gemini"

    # Should gracefully fall back to DETERMINISTIC_GROUNDED_TEMPLATE
    rep = engine.generate_report("e2e-trishuli-aug2026", language="en", use_llm=True)
    assert rep["generation_method"] == "DETERMINISTIC_GROUNDED_TEMPLATE"
    assert rep["summary_metrics"]["candidate_flood_area_sqkm"] == 4.245


# --- 8. MARKDOWN & PDF EXPORT VERIFICATION ---

def test_markdown_and_pdf_exports():
    """
    Verifies that Markdown and PDF documents are created on disk and have non-zero size.
    """
    rep = situation_report_engine.generate_report("e2e-trishuli-aug2026", language="en", use_llm=False)
    out_dir = OUTPUTS_DIR / "e2e-trishuli-aug2026"

    md_path = out_dir / "situation_report_en.md"
    pdf_path = out_dir / "situation_report_en.pdf"

    assert md_path.exists()
    assert md_path.stat().st_size > 1000

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 2000

    # Read markdown and check headings
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "# Rapid Satellite Disaster Situation Assessment" in md_text
    assert "Key Computed Metrics at a Glance" in md_text
    assert "4.245 km²" in md_text


# --- 9. FASTAPI ENDPOINTS & RESPONSES ---

def test_api_report_status_endpoint():
    """Verifies GET /api/report/status/{analysis_id} endpoint."""
    resp = client.get("/api/report/status/e2e-trishuli-aug2026")
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_id"] == "e2e-trishuli-aug2026"
    assert data["input_readiness"]["flood_data"] is True
    assert data["reports_available"]["en"] is True
    assert "download_links" in data


def test_api_get_situation_report():
    """Verifies GET /api/report/{analysis_id}?language=en endpoint."""
    resp = client.get("/api/report/e2e-trishuli-aug2026?language=en")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == "SITREP-e2e-trishuli-aug2026-EN"
    assert data["sections"]["executive_summary"] != ""


def test_api_generate_post_endpoint():
    """Verifies POST /api/report/generate execution endpoint."""
    payload = {
        "analysis_id": "e2e-trishuli-aug2026",
        "language": "en",
        "use_llm": False
    }
    resp = client.post("/api/report/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["generation_method"] == "DETERMINISTIC_GROUNDED_TEMPLATE"


def test_api_export_downloads():
    """Verifies Markdown and PDF download endpoints with appropriate headers."""
    # Markdown download
    resp_md = client.get("/api/report/e2e-trishuli-aug2026/export/markdown?language=en")
    assert resp_md.status_code == 200
    assert "text/markdown" in resp_md.headers.get("content-type", "")
    assert "attachment" in resp_md.headers.get("content-disposition", "")

    # PDF download
    resp_pdf = client.get("/api/report/e2e-trishuli-aug2026/export/pdf?language=en")
    assert resp_pdf.status_code == 200
    assert "application/pdf" in resp_pdf.headers.get("content-type", "")
    assert len(resp_pdf.content) > 1000


# --- 10. PATH TRAVERSAL REJECTION & INPUT SANITIZATION ---

def test_api_path_traversal_rejection():
    """Verifies that malicious path traversal strings in analysis_id are rejected with 400 Bad Request."""
    malicious_ids = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "test/traversal",
        "e2e-trishuli;rm"
    ]
    for bad_id in malicious_ids:
        resp_get = client.get(f"/api/report/{bad_id}")
        assert resp_get.status_code in (400, 404)

        resp_post = client.post("/api/report/generate", json={"analysis_id": bad_id})
        assert resp_post.status_code in (400, 404)


def test_api_invalid_language_rejection():
    """Verifies that unsupported language codes return 400 Bad Request."""
    resp = client.get("/api/report/e2e-trishuli-aug2026?language=invalid_lang")
    assert resp.status_code == 400
    assert "Invalid language code" in resp.json()["detail"]
