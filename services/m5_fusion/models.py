from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


SummaryStatus = Literal["draft", "edited", "signed"]


class SummaryItem(BaseModel):
    text: str
    provenance: list[str] = Field(default_factory=list)
    answered_by: Literal["self", "proxy", "unknown"] = "unknown"


class PrakritiSummary(BaseModel):
    vata: float = 0.0
    pitta: float = 0.0
    kapha: float = 0.0
    dominant: str = "unknown"
    confidence: float = 0.0
    provisional: bool = True
    items_answered: int = 0
    items_total: int = 0
    provenance: list[str] = Field(default_factory=list)


class AyushSummary(BaseModel):
    prakriti: PrakritiSummary = Field(default_factory=PrakritiSummary)
    vikriti: str | None = None
    agni: str | None = None
    koshtha: str | None = None
    ahara_vihara: list[str] = Field(default_factory=list)
    codes: dict[str, str | None] = Field(
        default_factory=lambda: {
            "namaste": None,
            "icd11_tm2": None,
        }
    )


class TimelineItem(BaseModel):
    date: str | None = None
    type: str
    text: str
    provenance: list[str] = Field(default_factory=list)


class DeltaSummary(BaseModel):
    is_return_visit: bool = False
    visit_number: int | None = None
    changed: list[str] = Field(default_factory=list)
    adherence_estimate: float | None = None
    adherence_category: str | None = None
    adherence_reason: str | None = None
    provenance: list[str] = Field(default_factory=list)


class GuardianMeta(BaseModel):
    checked: bool = False
    blocked_count: int = 0
    version: str | None = None


class ConflictFactModel(BaseModel):
    source_type: str
    value: Any
    provenance: list[str] = Field(default_factory=list)
    date: str | None = None
    text: str | None = None


class ConflictModel(BaseModel):
    conflict_type: str
    key: str
    facts: list[ConflictFactModel] = Field(default_factory=list)
    message: str


class ClinicalSummary(BaseModel):
    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    status: SummaryStatus = "draft"

    sections: dict[str, list[SummaryItem]] = Field(
        default_factory=lambda: {
            "chief_complaint": [],
            "hpi": [],
            "past_medical": [],
            "past_surgical": [],
            "drugs": [],
            "allergies": [],
            "family_history": [],
            "personal_history": [],
            "ros": [],
            "investigations": [],
        }
    )

    ayush: AyushSummary = Field(default_factory=AyushSummary)
    timeline: list[TimelineItem] = Field(default_factory=list)
    delta: DeltaSummary = Field(default_factory=DeltaSummary)

    conflicts: list[ConflictModel] = Field(default_factory=list)

    alerts: list[str] = Field(default_factory=list)
    guardian: GuardianMeta = Field(default_factory=GuardianMeta)

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    fields_dropped: int = 0


class SummariseRequest(BaseModel):
    slots: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    prior_encounter: dict[str, Any] | None = None
    is_return_visit: bool = False
    visit_number: int | None = None


class SummariseResponse(BaseModel):
    summary_id: str
    status: SummaryStatus
    fields_generated: int
    fields_dropped_unsourced: int
    conflicts_detected: int
    guardian_blocks: int
