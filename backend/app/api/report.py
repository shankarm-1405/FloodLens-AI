"""
Grounded AI Disaster Situation Report API Router
FloodLens AI - Phase 6: Operational Synthesis & Field Verification

Endpoints:
1. POST /api/report/generate: Triggers report generation with language and LLM options.
2. GET /api/report/{analysis_id}: Retrieves generated situation report JSON.
3. GET /api/report/{analysis_id}/status: Returns readiness of report artifacts.
4. GET /api/report/{analysis_id}/export/markdown: Downloads Markdown report.
5. GET /api/report/{analysis_id}/export/pdf: Downloads publication-quality PDF report.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.config import OUTPUTS_DIR
from app.core.infrastructure import validate_analysis_id
from app.core.situation_report import (
    situation_report_engine,
    ReportGenerationError,
    GroundingValidationError
)

router = APIRouter(prefix="/api/report", tags=["Grounded Situation Report Copilot"])


class GenerateReportRequest(BaseModel):
    analysis_id: str = Field(..., description="ID of a validated Sentinel-1 flood analysis")
    language: Optional[str] = Field(default="en", description="Report language: 'en' (English) or 'ne' (Nepali)")
    use_llm: Optional[bool] = Field(default=True, description="Attempt LLM generation with grounding verification if configured")


def validate_language(lang: Optional[str]) -> str:
    cleaned = (lang or "en").strip().lower()
    if cleaned not in ("en", "ne"):
        raise HTTPException(status_code=400, detail="Invalid language code. Must be 'en' (English) or 'ne' (Nepali).")
    return cleaned


@router.post("/generate")
def generate_situation_report(req: GenerateReportRequest) -> Dict[str, Any]:
    """
    Generates a grounded bilingual disaster situation report synthesizing flood extent,
    infrastructure exposure, and settlement disconnection metrics.
    """
    try:
        clean_id = validate_analysis_id(req.analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    lang = validate_language(req.language)

    try:
        report = situation_report_engine.generate_report(
            analysis_id=clean_id,
            language=lang,
            use_llm=req.use_llm if req.use_llm is not None else True
        )
        return report
    except ReportGenerationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@router.get("/status/{analysis_id}")
def get_report_status(analysis_id: str) -> Dict[str, Any]:
    """
    Checks the readiness of situation reports and underlying analysis artifacts.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_dir = OUTPUTS_DIR / clean_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    flood_ready = (analysis_dir / "analysis_metadata.json").exists()
    infra_ready = (analysis_dir / "infrastructure_exposure.json").exists()
    conn_ready = (analysis_dir / "connectivity_summary.json").exists()

    en_rep = analysis_dir / "situation_report_en.json"
    ne_rep = analysis_dir / "situation_report_ne.json"

    return {
        "analysis_id": clean_id,
        "input_readiness": {
            "flood_data": flood_ready,
            "infrastructure_data": infra_ready,
            "connectivity_data": conn_ready,
            "all_inputs_ready": flood_ready and infra_ready and conn_ready
        },
        "reports_available": {
            "en": en_rep.exists(),
            "ne": ne_rep.exists()
        },
        "download_links": {
            "markdown_en": f"/api/report/{clean_id}/export/markdown?language=en",
            "markdown_ne": f"/api/report/{clean_id}/export/markdown?language=ne",
            "pdf_en": f"/api/report/{clean_id}/export/pdf?language=en",
            "pdf_ne": f"/api/report/{clean_id}/export/pdf?language=ne"
        }
    }


@router.get("/{analysis_id}")
def get_situation_report(
    analysis_id: str,
    language: Optional[str] = Query(default=None, description="Language: 'en' or 'ne'"),
    lang: Optional[str] = Query(default=None, description="Alias for language: 'en' or 'ne'")
) -> Dict[str, Any]:
    """
    Retrieves the generated situation report. If not yet generated on disk, automatically generates it.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    target_lang = validate_language(language or lang or "en")
    analysis_dir = OUTPUTS_DIR / clean_id

    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    report_path = analysis_dir / f"situation_report_{target_lang}.json"

    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # If not on disk, generate now
    try:
        return situation_report_engine.generate_report(analysis_id=clean_id, language=target_lang, use_llm=False)
    except ReportGenerationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/{analysis_id}/export/markdown")
def export_markdown_report(
    analysis_id: str,
    language: Optional[str] = Query(default=None, description="Language: 'en' or 'ne'"),
    lang: Optional[str] = Query(default=None, description="Alias for language: 'en' or 'ne'")
):
    """
    Exports the grounded situation report as a downloadable Markdown document.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    target_lang = validate_language(language or lang or "en")
    analysis_dir = OUTPUTS_DIR / clean_id

    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    md_path = analysis_dir / f"situation_report_{target_lang}.md"

    if not md_path.exists():
        # Generate on the fly
        situation_report_engine.generate_report(analysis_id=clean_id, language=target_lang, use_llm=False)

    filename = f"situation_report_{clean_id}_{target_lang}.md"
    return FileResponse(
        path=str(md_path),
        filename=filename,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{analysis_id}/export/pdf")
def export_pdf_report(
    analysis_id: str,
    language: Optional[str] = Query(default=None, description="Language: 'en' or 'ne'"),
    lang: Optional[str] = Query(default=None, description="Alias for language: 'en' or 'ne'")
):
    """
    Exports the publication-quality situation report as a downloadable PDF document.
    """
    try:
        clean_id = validate_analysis_id(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    target_lang = validate_language(language or lang or "en")
    analysis_dir = OUTPUTS_DIR / clean_id

    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"Analysis ID '{clean_id}' not found.")

    pdf_path = analysis_dir / f"situation_report_{target_lang}.pdf"

    if not pdf_path.exists():
        # Generate on the fly
        situation_report_engine.generate_report(analysis_id=clean_id, language=target_lang, use_llm=False)

    filename = f"situation_report_{clean_id}_{target_lang}.pdf"
    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
