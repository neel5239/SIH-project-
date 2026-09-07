from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class DeltaResult:
    is_return_visit: bool
    visit_number: int | None
    changed: tuple[str, ...] = ()
    adherence_estimate: float | None = None
    adherence_category: str | None = None
    adherence_reason: str | None = None
    provenance: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_return_visit": self.is_return_visit,
            "visit_number": self.visit_number,
            "changed": list(self.changed),
            "adherence_estimate": self.adherence_estimate,
            "adherence_category": self.adherence_category,
            "adherence_reason": self.adherence_reason,
            "provenance": list(self.provenance),
        }


class DeltaEngine:
    """
    Deterministic M5 return-visit delta engine.

    Compares the current encounter with a supplied prior encounter.

    Supported comparisons:
    - symptom presence
    - symptom severity
    - new symptoms
    - drug changes
    - laboratory trends

    Adherence:
    - combines patient dosing report and refill-gap evidence
    - produces only an estimate
    - >80%  -> good
    - 40-80% -> partial
    - <40%  -> poor

    Safety:
    - no prior encounter -> no delta
    - no clinical facts are invented
    - adherence is never presented as a confirmed fact
    - no diagnosis
    - no treatment recommendation
    """

    def compare(
        self,
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any] | None,
        is_return_visit: bool,
        visit_number: int | None = None,
    ) -> DeltaResult:

        if not is_return_visit or prior is None:
            return DeltaResult(
                is_return_visit=is_return_visit,
                visit_number=visit_number,
            )

        changed: list[str] = []
        provenance: list[str] = []

        self._compare_symptoms(
            current=current,
            prior=prior,
            changed=changed,
            provenance=provenance,
        )

        self._compare_severity(
            current=current,
            prior=prior,
            changed=changed,
            provenance=provenance,
        )

        self._compare_new_symptoms(
            current=current,
            prior=prior,
            changed=changed,
            provenance=provenance,
        )

        self._compare_drugs(
            current=current,
            prior=prior,
            changed=changed,
            provenance=provenance,
        )

        self._compare_labs(
            current=current,
            prior=prior,
            changed=changed,
            provenance=provenance,
        )

        adherence = self._calculate_adherence(
            current=current,
            prior=prior,
            provenance=provenance,
        )

        return DeltaResult(
            is_return_visit=True,
            visit_number=visit_number,
            changed=tuple(dict.fromkeys(changed)),
            adherence_estimate=adherence["estimate"],
            adherence_category=adherence["category"],
            adherence_reason=adherence["reason"],
            provenance=tuple(dict.fromkeys(provenance)),
        )

    @staticmethod
    def _compare_symptoms(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        changed: list[str],
        provenance: list[str],
    ) -> None:
        current_symptoms = DeltaEngine._string_set(
            current.get("symptoms")
        )
        prior_symptoms = DeltaEngine._string_set(
            prior.get("symptoms")
        )

        for symptom in sorted(
            prior_symptoms - current_symptoms
        ):
            changed.append(
                f"Symptom no longer reported: {symptom}"
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "symptoms",
            )

        for symptom in sorted(
            current_symptoms & prior_symptoms
        ):
            changed.append(
                f"Symptom persists: {symptom}"
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "symptoms",
            )

    @staticmethod
    def _compare_severity(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        changed: list[str],
        provenance: list[str],
    ) -> None:
        current_severity = current.get("severity")
        prior_severity = prior.get("severity")

        if (
            isinstance(current_severity, (int, float))
            and isinstance(prior_severity, (int, float))
            and current_severity != prior_severity
        ):
            direction = (
                "increased"
                if current_severity > prior_severity
                else "decreased"
            )

            changed.append(
                f"Severity {direction}: "
                f"{prior_severity} -> {current_severity}"
            )

            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "severity",
            )

    @staticmethod
    def _compare_new_symptoms(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        changed: list[str],
        provenance: list[str],
    ) -> None:
        current_symptoms = DeltaEngine._string_set(
            current.get("symptoms")
        )
        prior_symptoms = DeltaEngine._string_set(
            prior.get("symptoms")
        )

        for symptom in sorted(
            current_symptoms - prior_symptoms
        ):
            changed.append(
                f"New symptom reported: {symptom}"
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "symptoms",
            )

    @staticmethod
    def _compare_drugs(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        changed: list[str],
        provenance: list[str],
    ) -> None:
        current_drugs = DeltaEngine._string_set(
            current.get("drugs")
        )
        prior_drugs = DeltaEngine._string_set(
            prior.get("drugs")
        )

        for drug in sorted(
            current_drugs - prior_drugs
        ):
            changed.append(
                f"Drug newly reported: {drug}"
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "drugs",
            )

        for drug in sorted(
            prior_drugs - current_drugs
        ):
            changed.append(
                f"Drug no longer reported: {drug}"
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "drugs",
            )

    @staticmethod
    def _compare_labs(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        changed: list[str],
        provenance: list[str],
    ) -> None:
        current_labs = current.get("labs")
        prior_labs = prior.get("labs")

        if (
            not isinstance(current_labs, Mapping)
            or not isinstance(prior_labs, Mapping)
        ):
            return

        for name in sorted(
            set(current_labs) & set(prior_labs)
        ):
            current_value = current_labs[name]
            prior_value = prior_labs[name]

            if (
                isinstance(current_value, (int, float))
                and isinstance(prior_value, (int, float))
                and current_value != prior_value
            ):
                direction = (
                    "increased"
                    if current_value > prior_value
                    else "decreased"
                )

                changed.append(
                    f"Lab {name} {direction}: "
                    f"{prior_value} -> {current_value}"
                )

                DeltaEngine._extend_provenance(
                    provenance,
                    current,
                    prior,
                    "labs",
                )

    @staticmethod
    def _calculate_adherence(
        *,
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        provenance: list[str],
    ) -> dict[str, Any]:
        dosing = DeltaEngine._numeric(
            current.get("dosing_adherence")
        )

        refill = DeltaEngine._numeric(
            current.get("refill_adherence")
        )

        values: list[float] = []

        if dosing is not None:
            values.append(
                DeltaEngine._clamp_percentage(dosing)
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "dosing_adherence",
            )

        if refill is not None:
            values.append(
                DeltaEngine._clamp_percentage(refill)
            )
            DeltaEngine._extend_provenance(
                provenance,
                current,
                prior,
                "refill_adherence",
            )

        if not values:
            return {
                "estimate": None,
                "category": None,
                "reason": None,
            }

        estimate = sum(values) / len(values)

        if estimate > 80:
            category = "good"
        elif estimate >= 40:
            category = "partial"
        else:
            category = "poor"

        sources = []

        if dosing is not None:
            sources.append("patient dosing report")

        if refill is not None:
            sources.append("refill-gap evidence")

        reason = (
            "Estimate based on "
            + " and ".join(sources)
            + "; not a confirmed fact."
        )

        return {
            "estimate": round(estimate, 2),
            "category": category,
            "reason": reason,
        }

    @staticmethod
    def _numeric(value: Any) -> float | None:
        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        return None

    @staticmethod
    def _clamp_percentage(value: float) -> float:
        return max(0.0, min(100.0, value))

    @staticmethod
    def _string_set(value: Any) -> set[str]:
        if not isinstance(value, (list, tuple, set)):
            return set()

        return {
            str(item).strip()
            for item in value
            if str(item).strip()
        }

    @staticmethod
    def _extend_provenance(
        target: list[str],
        current: Mapping[str, Any],
        prior: Mapping[str, Any],
        key: str,
    ) -> None:
        for source in (current, prior):
            refs = source.get(f"{key}_provenance", [])

            if isinstance(refs, str):
                refs = [refs]

            if isinstance(refs, (list, tuple, set)):
                target.extend(
                    str(ref).strip()
                    for ref in refs
                    if str(ref).strip()
                )
