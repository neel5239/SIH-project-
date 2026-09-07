from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NormalizedFact:
    section: str
    text: str
    provenance: list[str]
    answered_by: str = "unknown"
    source_type: str = "unknown"
    event_date: str | None = None


SECTION_KEYS = {
    "chief_complaint",
    "hpi",
    "past_medical",
    "past_surgical",
    "drugs",
    "allergies",
    "family_history",
    "personal_history",
    "ros",
    "investigations",
}


def _stringify(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_stringify(item) for item in value)

    if isinstance(value, dict):
        return ", ".join(
            f"{key}: {_stringify(item)}"
            for key, item in value.items()
        )

    if value is None:
        return ""

    if isinstance(value, bool):
        return "yes" if value else "no"

    return str(value)


def _slot_section(slot: dict[str, Any]) -> str:
    explicit = slot.get("section")
    if explicit in SECTION_KEYS:
        return explicit

    key = str(slot.get("ontology_key", ""))

    if key.startswith("cc.") or key.startswith("general.chief_complaint"):
        return "chief_complaint"

    if key.startswith(("hpi.", "socrates.")):
        return "hpi"

    if key.startswith(("pmh.", "past_medical.")):
        return "past_medical"

    if key.startswith(("psh.", "past_surgical.")):
        return "past_surgical"

    if key.startswith(("drugs.", "drug.")):
        return "drugs"

    if key.startswith(("allergy.", "allergies.")):
        return "allergies"

    if key.startswith(("family.", "family_history.")):
        return "family_history"

    if key.startswith(("personal.", "personal_history.")):
        return "personal_history"

    if key.startswith("ros."):
        return "ros"

    return "hpi"


def normalize_slot(slot: dict[str, Any]) -> NormalizedFact | None:
    value = slot.get("value")
    text = _stringify(value).strip()

    if not text:
        return None

    provenance_id = slot.get("provenance_id")

    if not provenance_id:
        return NormalizedFact(
            section=_slot_section(slot),
            text=text,
            provenance=[],
            answered_by=slot.get("answered_by", "unknown"),
            source_type="slot",
        )

    return NormalizedFact(
        section=_slot_section(slot),
        text=text,
        provenance=[str(provenance_id)],
        answered_by=slot.get("answered_by", "unknown"),
        source_type="M3",
    )


def _entity_section(entity: dict[str, Any]) -> str:
    entity_type = entity.get("entity_type")
    document_type = entity.get("document_type")

    if entity_type == "medicine":
        return "drugs"

    if entity_type == "lab_value":
        return "investigations"

    if entity_type == "diagnosis":
        return "past_medical"

    if entity_type == "procedure":
        return "past_surgical"

    if entity_type == "vital":
        return "investigations"

    if document_type in {"lab_report", "imaging_report"}:
        return "investigations"

    return "investigations"


def _entity_text(entity: dict[str, Any]) -> str:
    payload = entity.get("payload") or {}
    entity_type = entity.get("entity_type")

    if entity_type == "medicine":
        parts = [
            payload.get("name") or payload.get("normalised_name"),
            (
                f"{payload['strength']} {payload['strength_unit']}"
                if payload.get("strength") is not None
                and payload.get("strength_unit")
                else None
            ),
            payload.get("frequency"),
        ]
        return " ".join(str(part) for part in parts if part).strip()

    if entity_type == "lab_value":
        analyte = payload.get("analyte")
        value = payload.get("value")
        unit = payload.get("unit")
        if analyte and value is not None:
            return f"{analyte}: {value} {unit or ''}".strip()

    if entity_type in {"diagnosis", "procedure"}:
        return str(payload.get("text") or "").strip()

    if entity_type == "vital":
        name = payload.get("name")
        systolic = payload.get("systolic")
        diastolic = payload.get("diastolic")

        if name == "blood_pressure" and systolic is not None and diastolic is not None:
            return f"Blood pressure: {systolic}/{diastolic} mmHg"

        return _stringify(payload).strip()

    return (
        str(payload.get("text") or payload.get("raw_text") or "").strip()
    )


def normalize_entity(entity: dict[str, Any]) -> NormalizedFact | None:
    text = _entity_text(entity)

    if not text:
        return None

    provenance_id = (
        entity.get("provenance_id")
        or entity.get("source", {}).get("provenance_id")
        or entity.get("source", {}).get("prov_id")
    )

    return NormalizedFact(
        section=_entity_section(entity),
        text=text,
        provenance=[str(provenance_id)] if provenance_id else [],
        answered_by="unknown",
        source_type="M4",
        event_date=entity.get("event_date"),
    )
