from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, Text, String, JSON, LargeBinary, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def now():
    return datetime.now(timezone.utc)

class SessionRow(Base):
    __tablename__ = "sessions"
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    abha_id: Mapped[str|None] = mapped_column(String(64))
    patient_ref: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    language: Mapped[str] = mapped_column(String(8))
    opd_type: Mapped[str] = mapped_column(String(32))
    consent_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    token_number: Mapped[int] = mapped_column(Integer)
    kiosk_id: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32))
    phr_linked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_return_visit: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_encounter_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ConsentRow(Base):
    __tablename__ = "consents"
    consent_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    abha_id: Mapped[str|None] = mapped_column(String(64))
    consent_version: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))
    consent_text_hash: Mapped[str] = mapped_column(String(128))
    permissions: Mapped[dict] = mapped_column(JSON)
    assent_method: Mapped[str] = mapped_column(String(16))
    assent_audio_blob_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    operator_present: Mapped[bool] = mapped_column(Boolean)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    supersedes: Mapped[object|None] = mapped_column(UUID(as_uuid=True))

class SlotRow(Base):
    __tablename__ = "slots"
    slot_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    ontology_key: Mapped[str] = mapped_column(String(255))
    value: Mapped[dict] = mapped_column(JSON)
    value_type: Mapped[str] = mapped_column(String(32))
    unit: Mapped[str|None] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    framework: Mapped[str] = mapped_column(String(32))
    section: Mapped[str] = mapped_column(String(64))
    answered_by: Mapped[str] = mapped_column(String(16))
    input_mode: Mapped[str] = mapped_column(String(16))
    provenance_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ProvenanceRow(Base):
    __tablename__ = "provenance"
    prov_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(32))
    audio: Mapped[dict|None] = mapped_column(JSON)
    image: Mapped[dict|None] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class SummaryRow(Base):
    __tablename__ = "summaries"
    summary_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class CorrectionRow(Base):
    __tablename__ = "corrections"
    correction_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    summary_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    section: Mapped[str] = mapped_column(Text)
    field_path: Mapped[str] = mapped_column(Text)
    generated_value: Mapped[str|None] = mapped_column(Text)
    corrected_value: Mapped[str] = mapped_column(Text)
    source_module: Mapped[str|None] = mapped_column(Text)
    source_prov_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    corrected_by: Mapped[str] = mapped_column(Text)
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class TriageRow(Base):
    __tablename__ = "triage_queue"
    entry_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object] = mapped_column(UUID(as_uuid=True))
    token_number: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    reason: Mapped[str|None] = mapped_column(Text)
    rule_id: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str|None] = mapped_column(Text)
    acknowledged_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))

class AuditRow(Base):
    __tablename__ = "audit_log"
    event_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    actor_id: Mapped[str|None] = mapped_column(String(128))
    resource_id: Mapped[str|None] = mapped_column(String(128))
    session_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    metadata_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class JobRow(Base):
    __tablename__ = "jobs"
    job_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    type: Mapped[str] = mapped_column(Text)
    session_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    last_error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))

class OutboxRow(Base):
    __tablename__ = "fhir_outbox"
    outbox_id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[object|None] = mapped_column(UUID(as_uuid=True))
    resource_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
