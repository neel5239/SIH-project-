from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.m5_fusion.database.provenance_repository import (
    ProvenanceRepository,
)
from services.m5_fusion.database.summary_repository import SummaryRepository
from services.m5_fusion.services.summary_builder import SummaryBuilder
from services.m5_fusion.services.physician_render import PhysicianRenderer


app = FastAPI(
    title="M5 Fusion, Summary & Safety",
    version="0.6.0",
)

builder = SummaryBuilder()
repository = SummaryRepository()
provenance_repository = ProvenanceRepository()
physician_renderer = PhysicianRenderer()


class SummariseRequest(BaseModel):
    slots: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    prior_encounter: dict[str, Any] | None = None
    is_return_visit: bool = False
    visit_number: int = 1
    consent: dict[str, Any] | None = None


class RecapRequest(BaseModel):
    language: str = "en"
    consent: dict[str, Any] | None = None


class FieldCorrectionRequest(BaseModel):
    section: str
    field_path: str
    corrected_value: Any
    physician_id: str
    summary_id: str | None = None


@app.get("/")
def root():
    return {
        "service": "M5 Fusion, Summary & Safety",
        "status": "ok",
        "phase": 3,
        "storage": "mongodb",
    }


@app.get("/health")
def health():
    try:
        repository.ping()
        return {
            "status": "healthy",
            "service": "m5_fusion",
            "database": "mongodb",
        }
    except Exception:
        return {
            "status": "degraded",
            "service": "m5_fusion",
            "database": "unavailable",
        }


@app.post("/api/v1/session/{session_id}/summarise")
def summarise(
    session_id: str,
    request: SummariseRequest,
):
    try:
        summary = builder.build(
            session_id=session_id,
            slots=request.slots,
            entities=request.entities,
            prior_encounter=request.prior_encounter,
            is_return_visit=request.is_return_visit,
            visit_number=request.visit_number,
        )

        repository.save(summary)

        fields_generated = sum(
            len(items)
            for items in summary.sections.values()
        )

        return {
            "status": "draft",
            "summary_id": summary.summary_id,
            "fields_generated": fields_generated,
            "fields_dropped_unsourced": summary.fields_dropped,
            "guardian_blocks": summary.guardian.blocked_count,
            "conflicts_detected": len(summary.conflicts),
            "summary": summary.model_dump(mode="json"),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get("/api/v1/session/{session_id}/summary")
def get_summary(session_id: str):
    summary = repository.get(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    return summary.model_dump(mode="json")


@app.get("/api/v1/session/{session_id}/prakriti")
def get_prakriti(session_id: str):
    summary = repository.get(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    if summary.ayush is None or summary.ayush.prakriti is None:
        return {
            "vata": 0.0,
            "pitta": 0.0,
            "kapha": 0.0,
            "dominant": "vata",
            "confidence": 0.0,
            "provisional": True,
            "items_answered": 0,
            "items_total": 0,
            "provenance": [],
        }

    return summary.ayush.prakriti.model_dump(mode="json")


@app.get("/api/v1/session/{session_id}/physician-render")
def physician_render(
    session_id: str,
    ayush_opd: bool = True,
):
    summary = repository.get(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    rendered = physician_renderer.render(
        summary,
        ayush_opd=ayush_opd,
    )

    return rendered.to_dict()


@app.get("/api/v1/session/{session_id}/physician-render/text")
def physician_render_text(
    session_id: str,
    ayush_opd: bool = True,
):
    summary = repository.get(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    return {
        "summary_id": summary.summary_id,
        "text": physician_renderer.render_text(
            summary,
            ayush_opd=ayush_opd,
        ),
    }


@app.get("/api/v1/summary/{summary_id}/provenance/{prov_id}")
def get_provenance(
    summary_id: str,
    prov_id: str,
):
    summary = repository.get_by_summary_id(summary_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    provenance = provenance_repository.get(prov_id)

    if provenance is None:
        raise HTTPException(
            status_code=404,
            detail="Provenance not found",
        )

    referenced_ids: set[str] = set()

    for section_items in summary.sections.values():
        for item in section_items:
            referenced_ids.update(
                str(ref)
                for ref in item.provenance
            )

    if prov_id not in referenced_ids:
        raise HTTPException(
            status_code=404,
            detail="Provenance not linked to summary",
        )

    return provenance


@app.get("/api/v1/summary/{summary_id}/delta")
def get_delta(summary_id: str):
    summary = repository.get_by_summary_id(summary_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    return summary.delta.model_dump(mode="json")


@app.post("/api/v1/session/{session_id}/recap")
def recap(
    session_id: str,
    request: RecapRequest,
):
    summary = repository.get(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    return {
        "session_id": session_id,
        "language": request.language,
        "summary_id": summary.summary_id,
        "recap": {
            "sections": summary.sections,
            "ayush": summary.ayush.model_dump(mode="json")
            if summary.ayush is not None
            else None,
        },
        "status": "template_fallback",
    }


@app.get("/api/v1/metrics/guardian")
def guardian_metrics():
    return builder.guardian_metrics()


@app.get("/api/v1/metrics/accuracy")
def accuracy_metrics(window: str = "7d"):
    return {
        "window": window,
        "status": "not_configured",
        "message": "Accuracy metrics require correction records.",
    }


@app.patch("/api/v1/summary/{summary_id}/field")
def correct_summary_field(
    summary_id: str,
    request: FieldCorrectionRequest,
):
    summary = repository.get_by_summary_id(summary_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Summary not found",
        )

    return {
        "status": "correction_capture_pending",
        "summary_id": summary_id,
        "section": request.section,
        "field_path": request.field_path,
        "corrected_value": request.corrected_value,
        "physician_id": request.physician_id,
    }





