from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConflictFact:
    source_type: str
    value: Any
    provenance: list[str] = field(default_factory=list)
    date: str | None = None
    text: str | None = None


@dataclass
class Conflict:
    conflict_type: str
    key: str
    facts: list[ConflictFact]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_type": self.conflict_type,
            "key": self.key,
            "facts": [
                {
                    "source_type": fact.source_type,
                    "value": fact.value,
                    "provenance": fact.provenance,
                    "date": fact.date,
                    "text": fact.text,
                }
                for fact in self.facts
            ],
            "message": self.message,
        }


class ConflictResolver:
    """
    M5 conflict resolver.

    Safety rule:
        conflicting facts are NEVER merged and NEVER silently resolved.

    The resolver only identifies conflicts and returns all contributing
    facts with their provenance.
    """

    def resolve(
        self,
        *,
        slots: list[dict[str, Any]] | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> list[Conflict]:

        normalized: dict[str, list[ConflictFact]] = {}

        for slot in slots or []:
            key = self._slot_key(slot)
            if not key:
                continue

            normalized.setdefault(key, []).append(
                ConflictFact(
                    source_type="M3",
                    value=slot.get("value"),
                    provenance=self._provenance(slot),
                    date=slot.get("date") or slot.get("event_date"),
                    text=slot.get("raw_text"),
                )
            )

        for entity in entities or []:
            key = self._entity_key(entity)
            if not key:
                continue

            normalized.setdefault(key, []).append(
                ConflictFact(
                    source_type="M4",
                    value=self._entity_value(entity),
                    provenance=self._provenance(entity),
                    date=entity.get("date") or entity.get("event_date"),
                    text=entity.get("text"),
                )
            )

        conflicts: list[Conflict] = []

        for key, facts in normalized.items():
            if len(facts) < 2:
                continue

            if self._has_cross_source_denial_conflict(facts):
                conflicts.append(
                    Conflict(
                        conflict_type="denial_vs_documentary",
                        key=key,
                        facts=facts,
                        message=(
                            "Patient-reported denial conflicts with "
                            "documentary evidence."
                        ),
                    )
                )
                continue

            if self._has_contradictory_values(facts):
                conflicts.append(
                    Conflict(
                        conflict_type="contradictory_values",
                        key=key,
                        facts=facts,
                        message="Sources contain contradictory values.",
                    )
                )

        conflicts.extend(
            self._detect_drug_list_mismatch(
                slots or [],
                entities or [],
            )
        )

        return conflicts

    @staticmethod
    def _slot_key(slot: dict[str, Any]) -> str | None:
        key = slot.get("ontology_key") or slot.get("key")
        if not key:
            return None

        # Diabetes/other PMH facts should remain grouped with their
        # corresponding document evidence.
        return str(key).strip()

    @staticmethod
    def _entity_key(entity: dict[str, Any]) -> str | None:
        explicit = entity.get("ontology_key") or entity.get("key")
        if explicit:
            return str(explicit).strip()

        entity_type = entity.get("entity_type")

        if entity_type == "medicine":
            payload = entity.get("payload") or {}
            name = (
                payload.get("normalised_name")
                or payload.get("name")
            )
            if name:
                return f"drug:{str(name).strip().lower()}"

        if entity_type == "diagnosis":
            payload = entity.get("payload") or {}
            text = payload.get("text") or payload.get("name")
            if text:
                return f"diagnosis:{str(text).strip().lower()}"

        return None

    @staticmethod
    def _entity_value(entity: dict[str, Any]) -> Any:
        payload = entity.get("payload") or {}

        if entity.get("entity_type") == "medicine":
            return {
                "name": (
                    payload.get("normalised_name")
                    or payload.get("name")
                ),
                "strength": payload.get("strength"),
                "strength_unit": payload.get("strength_unit"),
                "frequency": payload.get("frequency"),
            }

        return payload.get("text") or payload.get("name") or payload

    @staticmethod
    def _provenance(record: dict[str, Any]) -> list[str]:
        direct = record.get("provenance_id")
        if direct:
            return [str(direct)]

        provenance = record.get("provenance")

        if isinstance(provenance, list):
            return [str(value) for value in provenance if value]

        if isinstance(provenance, str):
            return [provenance]

        source = record.get("source") or {}
        source_id = (
            source.get("provenance_id")
            or source.get("prov_id")
        )

        if source_id:
            return [str(source_id)]

        return []

    @staticmethod
    def _is_denial(value: Any) -> bool:
        if isinstance(value, bool):
            return value is False

        if isinstance(value, str):
            text = value.strip().lower()
            return text in {
                "no",
                "none",
                "negative",
                "denies",
                "denied",
                "false",
                "not present",
                "no history",
                "nil",
            }

        return False

    @staticmethod
    def _has_cross_source_denial_conflict(
        facts: list[ConflictFact],
    ) -> bool:
        has_m3_denial = any(
            fact.source_type == "M3"
            and ConflictResolver._is_denial(fact.value)
            for fact in facts
        )

        has_m4_evidence = any(
            fact.source_type == "M4"
            and fact.value not in (None, "", [], {})
            for fact in facts
        )

        return has_m3_denial and has_m4_evidence

    @staticmethod
    def _canonical(value: Any) -> str:
        if isinstance(value, dict):
            return repr(
                sorted(
                    (str(key), ConflictResolver._canonical(item))
                    for key, item in value.items()
                )
            )

        if isinstance(value, list):
            return repr(
                sorted(
                    ConflictResolver._canonical(item)
                    for item in value
                )
            )

        return str(value).strip().lower()

    @classmethod
    def _has_contradictory_values(
        cls,
        facts: list[ConflictFact],
    ) -> bool:
        values = {
            cls._canonical(fact.value)
            for fact in facts
            if fact.value not in (None, "", [], {})
        }

        if len(values) <= 1:
            return False

        # A denial/documentary case is handled separately.
        if cls._has_cross_source_denial_conflict(facts):
            return False

        return True

    @classmethod
    def _detect_drug_list_mismatch(
        cls,
        slots: list[dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> list[Conflict]:

        patient_drugs: set[str] = set()

        for slot in slots:
            key = str(
                slot.get("ontology_key")
                or slot.get("key")
                or ""
            ).lower()

            if not (
                key.startswith("drug")
                or key.startswith("medication")
                or "medicine" in key
            ):
                continue

            value = slot.get("value")

            if isinstance(value, list):
                patient_drugs.update(
                    str(item).strip().lower()
                    for item in value
                    if item
                )
            elif value:
                patient_drugs.add(str(value).strip().lower())

        document_drugs: set[str] = set()

        for entity in entities:
            if entity.get("entity_type") != "medicine":
                continue

            payload = entity.get("payload") or {}

            name = (
                payload.get("normalised_name")
                or payload.get("name")
            )

            if name:
                document_drugs.add(str(name).strip().lower())

        if not patient_drugs or not document_drugs:
            return []

        if patient_drugs == document_drugs:
            return []

        all_facts = [
            ConflictFact(
                source_type="M3",
                value=sorted(patient_drugs),
                provenance=cls._combined_slot_provenance(slots),
            ),
            ConflictFact(
                source_type="M4",
                value=sorted(document_drugs),
                provenance=cls._combined_entity_provenance(entities),
            ),
        ]

        return [
            Conflict(
                conflict_type="drug_list_mismatch",
                key="drugs",
                facts=all_facts,
                message=(
                    "Patient-reported and documentary medication lists "
                    "do not match."
                ),
            )
        ]

    @staticmethod
    def _combined_slot_provenance(
        slots: list[dict[str, Any]],
    ) -> list[str]:
        refs: list[str] = []

        for slot in slots:
            ref = slot.get("provenance_id")
            if ref:
                refs.append(str(ref))

        return refs

    @staticmethod
    def _combined_entity_provenance(
        entities: list[dict[str, Any]],
    ) -> list[str]:
        refs: list[str] = []

        for entity in entities:
            if entity.get("entity_type") != "medicine":
                continue

            direct = entity.get("provenance_id")
            source = entity.get("source") or {}

            ref = direct or source.get("provenance_id") or source.get("prov_id")

            if ref:
                refs.append(str(ref))

        return refs
