from __future__ import annotations

from typing import Any

from services.m5_fusion.models import (
    ClinicalSummary,
    ConflictModel,
    DeltaSummary,
    PrakritiSummary,
    SummaryItem,
    TimelineItem,
)
from services.m5_fusion.services.conflict_resolver import ConflictResolver
from services.m5_fusion.services.delta_engine import DeltaEngine
from services.m5_fusion.services.dual_coding import DualCodingService
from services.m5_fusion.services.guardian import GuardianGate
from services.m5_fusion.services.normalizer import (
    normalize_entity,
    normalize_slot,
)
from services.m5_fusion.services.prakriti import PrakritiScorer
from services.m5_fusion.services.provenance_binder import ProvenanceBinder
from services.m5_fusion.services.schema_generator import (
    SchemaConstrainedGenerator,
    SchemaGenerationError,
)


class SummaryBuilder:
    """
    M5 deterministic summary pipeline.

    Pipeline:
        normalize
        -> conflict detection
        -> schema generation
        -> provenance binding
        -> Guardian
        -> delta
        -> final ClinicalSummary

    Safety:
    - unsourced facts are discarded
    - invalid provenance is discarded
    - conflicts are never silently resolved
    - generator failure uses deterministic sourced fallback
    - Guardian blocks diagnostic/therapeutic output
    - Guardian failure fails closed
    - delta only compares supplied encounter data
    - adherence is always an estimate
    - no diagnosis or treatment generation
    """

    def __init__(
        self,
        conflict_resolver: ConflictResolver | None = None,
        prakriti_scorer: PrakritiScorer | None = None,
        dual_coding_service: DualCodingService | None = None,
        schema_generator: SchemaConstrainedGenerator | None = None,
        provenance_binder: ProvenanceBinder | None = None,
        guardian: GuardianGate | None = None,
        delta_engine: DeltaEngine | None = None,
    ):
        self.conflict_resolver = (
            conflict_resolver or ConflictResolver()
        )
        self.prakriti_scorer = (
            prakriti_scorer or PrakritiScorer()
        )
        self.dual_coding_service = (
            dual_coding_service or DualCodingService()
        )
        self.schema_generator = (
            schema_generator or SchemaConstrainedGenerator()
        )
        self.provenance_binder = provenance_binder
        self.guardian = guardian or GuardianGate()
        self.delta_engine = delta_engine or DeltaEngine()

    def build(
        self,
        *,
        session_id: str,
        slots: list[dict[str, Any]] | None = None,
        entities: list[dict[str, Any]] | None = None,
        prior_encounter: dict[str, Any] | None = None,
        is_return_visit: bool = False,
        visit_number: int | None = None,
        provenance_store: dict[str, dict[str, Any]] | None = None,
    ) -> ClinicalSummary:

        slots = slots or []
        entities = entities or []

        summary = ClinicalSummary(
            session_id=session_id,
            delta=DeltaSummary(
                is_return_visit=is_return_visit,
                visit_number=visit_number,
            ),
        )

        dropped = 0
        guardian_blocked = 0

        candidate_sections: dict[str, list[dict[str, Any]]] = {
            section: []
            for section in summary.sections
        }

        # ---------------------------------------------------------
        # Normalize M3 slots
        # ---------------------------------------------------------
        for raw_slot in slots:
            fact = normalize_slot(raw_slot)

            if fact is None:
                continue

            if not fact.provenance:
                dropped += 1
                continue

            candidate_sections[fact.section].append(
                {
                    "text": fact.text,
                    "provenance": fact.provenance,
                    "answered_by": (
                        fact.answered_by
                        if fact.answered_by in {"self", "proxy"}
                        else "unknown"
                    ),
                }
            )

        # ---------------------------------------------------------
        # Normalize M4 entities
        # ---------------------------------------------------------
        for raw_entity in entities:
            fact = normalize_entity(raw_entity)

            if fact is None:
                continue

            if not fact.provenance:
                dropped += 1
                continue

            candidate_sections[fact.section].append(
                {
                    "text": fact.text,
                    "provenance": fact.provenance,
                    "answered_by": "unknown",
                }
            )

            if fact.event_date:
                summary.timeline.append(
                    TimelineItem(
                        date=fact.event_date,
                        type=raw_entity.get(
                            "document_type",
                            raw_entity.get(
                                "entity_type",
                                "document",
                            ),
                        ),
                        text=fact.text,
                        provenance=fact.provenance,
                    )
                )

        # ---------------------------------------------------------
        # Schema-constrained generation
        # ---------------------------------------------------------
        try:
            generated_sections = self.schema_generator.generate(
                sections=candidate_sections
            )
        except SchemaGenerationError:
            generated_sections = candidate_sections

        # ---------------------------------------------------------
        # Provenance binding
        # ---------------------------------------------------------
        if provenance_store is not None:
            binder = ProvenanceBinder(provenance_store)
        else:
            binder = self.provenance_binder

        if binder is not None:
            bound_sections: dict[str, list[dict[str, Any]]] = {}

            for section, items in generated_sections.items():
                bound_items = binder.bind_and_filter(items)
                bound_sections[section] = [
                    item.to_dict()
                    for item in bound_items
                ]

            dropped += binder.dropped_count
            generated_sections = bound_sections

        # ---------------------------------------------------------
        # Guardian safety gate
        # ---------------------------------------------------------
        guardian_sections: dict[str, list[dict[str, Any]]] = {}

        for section, items in generated_sections.items():
            guardian_sections[section] = []

            for item in items:
                text = item.get("text")

                try:
                    result = self.guardian.check_or_fail_closed(text)
                except Exception:
                    result = None
                    guardian_blocked += 1

                if result is None or not result.allowed:
                    if result is not None:
                        guardian_blocked += 1
                    continue

                guardian_sections[section].append(item)

        generated_sections = guardian_sections

        # ---------------------------------------------------------
        # Rebuild fixed Pydantic ClinicalSummary sections
        # ---------------------------------------------------------
        for section in summary.sections:
            summary.sections[section] = [
                SummaryItem.model_validate(item)
                for item in generated_sections.get(section, [])
            ]

        # ---------------------------------------------------------
        # Guardian metadata
        # ---------------------------------------------------------
        summary.guardian.checked = True
        summary.guardian.blocked_count = guardian_blocked
        summary.guardian.version = getattr(
            self.guardian,
            "version",
            "unknown",
        )

        # ---------------------------------------------------------
        # M5 Prakriti scoring
        # ---------------------------------------------------------
        sourced_prakriti_slots = [
            slot
            for slot in slots
            if str(slot.get("ontology_key", "")).startswith(
                "ayush.prakriti."
            )
            and slot.get("provenance_id")
        ]

        prakriti_result = self.prakriti_scorer.score(
            sourced_prakriti_slots
        )

        summary.ayush.prakriti = PrakritiSummary(
            vata=prakriti_result.vata,
            pitta=prakriti_result.pitta,
            kapha=prakriti_result.kapha,
            dominant=prakriti_result.dominant,
            confidence=prakriti_result.confidence,
            provisional=prakriti_result.provisional,
            items_answered=prakriti_result.answered_questions,
            items_total=prakriti_result.items_total,
            provenance=prakriti_result.provenance,
        )

        # ---------------------------------------------------------
        # M5 Dual Coding
        # ---------------------------------------------------------
        ayush_condition_candidates = [
            slot
            for slot in slots
            if (
                str(slot.get("ontology_key", "")).startswith(
                    "ayush."
                )
                and slot.get("provenance_id")
                and isinstance(slot.get("value"), str)
            )
            and any(
                token in str(slot.get("ontology_key", "")).lower()
                for token in (
                    "condition",
                    "diagnosis",
                    "disease",
                    "disorder",
                )
            )
        ]

        for condition_slot in ayush_condition_candidates:
            mapping = self.dual_coding_service.lookup(
                str(condition_slot["value"])
            )

            if mapping is None:
                continue

            summary.ayush.codes = {
                "namaste": mapping.namaste_code,
                "icd11_tm2": mapping.icd11_tm2_code,
            }

            break

        # ---------------------------------------------------------
        # Conflict resolution
        # ---------------------------------------------------------
        conflicts = self.conflict_resolver.resolve(
            slots=slots,
            entities=entities,
        )

        summary.conflicts = [
            ConflictModel.model_validate(
                conflict.to_dict()
            )
            for conflict in conflicts
        ]

        summary.alerts = [
            f"Conflict requires physician review: {conflict.key}"
            for conflict in conflicts
        ]

        # ---------------------------------------------------------
        # M5 Delta + adherence
        # ---------------------------------------------------------
        delta_current = self._build_delta_current(
            slots=slots,
            entities=entities,
        )

        delta_result = self.delta_engine.compare(
            current=delta_current,
            prior=prior_encounter,
            is_return_visit=is_return_visit,
            visit_number=visit_number,
        )

        summary.delta = DeltaSummary(
            is_return_visit=delta_result.is_return_visit,
            visit_number=delta_result.visit_number,
            changed=list(delta_result.changed),
            adherence_estimate=delta_result.adherence_estimate,
            adherence_category=delta_result.adherence_category,
            adherence_reason=delta_result.adherence_reason,
            provenance=list(delta_result.provenance),
        )

        summary.fields_dropped = dropped

        return summary

    @staticmethod
    def _build_delta_current(
        *,
        slots: list[dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Convert currently sourced M3/M4 facts into the small,
        deterministic input contract expected by DeltaEngine.

        Unknown fields are simply omitted.
        """

        current: dict[str, Any] = {}

        symptoms: list[str] = []
        drugs: list[str] = []

        symptom_provenance: list[str] = []
        drug_provenance: list[str] = []

        for slot in slots:
            if not slot.get("provenance_id"):
                continue

            ontology_key = str(
                slot.get("ontology_key", "")
            ).lower()

            value = slot.get("value")

            if isinstance(value, str):
                clean_value = value.strip()

                if not clean_value:
                    continue

                if "symptom" in ontology_key:
                    symptoms.append(clean_value)
                    symptom_provenance.append(
                        str(slot["provenance_id"])
                    )

                if "drug" in ontology_key or "medication" in ontology_key:
                    drugs.append(clean_value)
                    drug_provenance.append(
                        str(slot["provenance_id"])
                    )

                if "severity" in ontology_key:
                    try:
                        current["severity"] = float(clean_value)
                        current.setdefault(
                            "severity_provenance",
                            [],
                        ).append(
                            str(slot["provenance_id"])
                        )
                    except ValueError:
                        pass

            elif isinstance(value, (int, float)) and not isinstance(
                value,
                bool,
            ):
                if "severity" in ontology_key:
                    current["severity"] = value
                    current.setdefault(
                        "severity_provenance",
                        [],
                    ).append(
                        str(slot["provenance_id"])
                    )

                if "adherence" in ontology_key:
                    current["dosing_adherence"] = value
                    current.setdefault(
                        "dosing_adherence_provenance",
                        [],
                    ).append(
                        str(slot["provenance_id"])
                    )

        if symptoms:
            current["symptoms"] = list(dict.fromkeys(symptoms))
            current["symptoms_provenance"] = list(
                dict.fromkeys(symptom_provenance)
            )

        if drugs:
            current["drugs"] = list(dict.fromkeys(drugs))
            current["drugs_provenance"] = list(
                dict.fromkeys(drug_provenance)
            )

        return current

    @staticmethod
    def count_generated(
        summary: ClinicalSummary,
    ) -> int:
        return sum(
            len(items)
            for items in summary.sections.values()
        )

