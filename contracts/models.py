from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Permissions(BaseModel):
    capture: bool
    share_his: bool
    push_phr: bool
    retain_audio: bool = False


class Session(BaseModel):
    session_id: UUID
    abha_id: str | None = None
    patient_ref: UUID | None = None
    language: str
    opd_type: Literal["allopathic", "ayush"]
    consent_id: UUID
    token_number: int
    kiosk_id: str
    state: Literal[
        "created", "consented", "interviewing", "scanning",
        "summarising", "complete", "aborted"
    ]
    phr_linked: bool = False
    is_return_visit: bool = False
    previous_encounter_id: UUID | None = None
    started_at: datetime
    expires_at: datetime


class Consent(BaseModel):
    consent_id: UUID
    session_id: UUID
    abha_id: str | None = None
    consent_version: str
    language: str
    consent_text_hash: str
    permissions: Permissions
    assent_method: Literal["voice", "touch"]
    assent_audio_blob_id: UUID | None = None
    operator_present: bool = False
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    supersedes: UUID | None = None


class Slot(BaseModel):
    slot_id: UUID
    session_id: UUID
    ontology_key: str
    value: Any
    value_type: Literal[
        "string", "number", "boolean", "enum", "enum_multi", "scale"
    ]
    unit: str | None = None
    confidence: float = Field(ge=0, le=1)
    framework: Literal[
        "socrates", "ros", "dashavidha", "demographics", "general"
    ]
    section: str
    answered_by: Literal["self", "proxy"] = "self"
    input_mode: Literal["voice", "touch"]
    provenance_id: UUID | None = None
    created_at: datetime


class DocumentSource(BaseModel):
    type: Literal["image_bbox"]
    page: int
    bbox: list[int]
    crop_blob_id: UUID


class DocEntity(BaseModel):
    entity_id: UUID
    session_id: UUID
    document_id: UUID
    entity_type: Literal[
        "medicine", "diagnosis", "lab_value", "procedure", "vital"
    ]
    payload: dict[str, Any]
    confidence: float = Field(ge=0, le=1)
    needs_verification: bool = False
    source: DocumentSource
    created_at: datetime


class Provenance(BaseModel):
    prov_id: UUID
    session_id: UUID
    kind: Literal[
        "audio_offset", "image_bbox", "physician_entry"
    ]
    audio: dict[str, Any] | None = None
    image: dict[str, Any] | None = None
    created_by: Literal["M3", "M4", "physician"]
    created_at: datetime


class Alert(BaseModel):
    alert_id: UUID
    session_id: UUID
    kind: Literal[
        "red_flag", "conflict", "abnormal_value",
        "unreadable", "interaction"
    ]
    severity: Literal["critical", "warning", "info"]
    rule_id: str | None = None
    title: str
    detail: str
    evidence_refs: list[str]
    raised_by: Literal["M3", "M4", "M5"]
    raised_at: datetime
    acknowledged_by: str | None = None


class ClinicalSummary(BaseModel):
    summary_id: UUID
    session_id: UUID
    status: Literal["draft", "edited", "signed"]
    sections: dict[str, list[dict[str, Any]]]
    ayush: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] = []
    delta: dict[str, Any] | None = None
    alerts: list[str] = []
    guardian: dict[str, Any]
    generated_at: datetime


class Correction(BaseModel):
    correction_id: UUID
    summary_id: UUID
    section: str
    field_path: str
    generated_value: str | None
    corrected_value: str
    source_module: str | None
    source_provenance: UUID | None
    corrected_by: str
    corrected_at: datetime
