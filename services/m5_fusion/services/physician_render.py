from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.m5_fusion.models import ClinicalSummary, SummaryItem


@dataclass(frozen=True)
class PhysicianRender:
    """
    Deterministic physician-facing representation of a ClinicalSummary.

    Safety:
    - never creates clinical facts
    - never diagnoses
    - never recommends treatment
    - renders only summary data already approved by M5
    - provenance is displayed with every rendered clinical item
    """

    sections: dict[str, list[str]]
    alerts: list[str]
    ayush: dict[str, Any]
    timeline: list[str]
    delta: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sections": self.sections,
            "alerts": self.alerts,
            "ayush": self.ayush,
            "timeline": self.timeline,
            "delta": self.delta,
        }


class PhysicianRenderer:
    """
    Builds a compact, deterministic physician-facing render.

    Section order follows the M5 specification:
        CC -> HPI -> PMH/PSH -> Drugs/Allergy -> Family ->
        Personal -> ROS -> Investigations -> AYUSH -> Timeline -> Delta
    """

    SECTION_LABELS = {
        "chief_complaint": "Chief Complaint",
        "hpi": "HPI",
        "past_medical": "Past Medical History",
        "past_surgical": "Past Surgical History",
        "drugs": "Drugs",
        "allergies": "Allergies",
        "family_history": "Family History",
        "personal_history": "Personal History",
        "ros": "Review of Systems",
        "investigations": "Investigations",
    }

    SECTION_ORDER = (
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
    )

    def render(
        self,
        summary: ClinicalSummary,
        *,
        ayush_opd: bool = True,
    ) -> PhysicianRender:

        sections: dict[str, list[str]] = {}

        for section in self.SECTION_ORDER:
            items = summary.sections.get(section, [])

            rendered_items = [
                self._render_item(item)
                for item in items
            ]

            sections[self.SECTION_LABELS[section]] = rendered_items

        alerts = [
            str(alert).strip()
            for alert in summary.alerts
            if isinstance(alert, str) and alert.strip()
        ]

        ayush = self._render_ayush(
            summary,
            enabled=ayush_opd,
        )

        timeline = [
            self._render_timeline_item(item)
            for item in summary.timeline
        ]

        delta = self._render_delta(summary)

        return PhysicianRender(
            sections=sections,
            alerts=alerts,
            ayush=ayush,
            timeline=timeline,
            delta=delta,
        )

    def render_text(
        self,
        summary: ClinicalSummary,
        *,
        ayush_opd: bool = True,
    ) -> str:
        """
        Produce a scannable plain-text physician view.

        Every clinical item retains its provenance marker.
        """

        rendered = self.render(
            summary,
            ayush_opd=ayush_opd,
        )

        lines: list[str] = []

        # Alerts intentionally appear first.
        if rendered.alerts:
            lines.append("ALERTS")
            for alert in rendered.alerts:
                lines.append(f"! {alert}")
            lines.append("")

        for label, items in rendered.sections.items():
            if not items:
                continue

            lines.append(label.upper())

            for item in items:
                lines.append(f"- {item}")

            lines.append("")

        if rendered.ayush:
            lines.append("AYUSH")
            for key, value in rendered.ayush.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        if rendered.timeline:
            lines.append("TIMELINE")
            for item in rendered.timeline:
                lines.append(f"- {item}")
            lines.append("")

        if rendered.delta:
            lines.append("DELTA")
            for item in rendered.delta:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def _render_item(
        item: SummaryItem,
    ) -> str:
        text = item.text.strip()

        proxy_marker = ""
        if item.answered_by == "proxy":
            proxy_marker = " [PROXY]"

        provenance = ", ".join(
            ref.strip()
            for ref in item.provenance
            if ref and ref.strip()
        )

        # A SummaryItem without provenance should never normally reach
        # this renderer. Fail closed rather than rendering it.
        if not provenance:
            return "[UNRENDERED: missing provenance]"

        return (
            f"{text}{proxy_marker}"
            f" [source: {provenance}]"
        )

    @staticmethod
    def _render_timeline_item(item) -> str:
        provenance = ", ".join(
            ref.strip()
            for ref in item.provenance
            if ref and ref.strip()
        )

        if not provenance:
            return "[UNRENDERED: missing provenance]"

        date = item.date or "undated"

        return (
            f"{date} | {item.type} | {item.text}"
            f" [source: {provenance}]"
        )

    @staticmethod
    def _render_ayush(
        summary: ClinicalSummary,
        *,
        enabled: bool,
    ) -> dict[str, Any]:
        if not enabled:
            return {}

        prakriti = summary.ayush.prakriti

        result: dict[str, Any] = {
            "prakriti": {
                "vata": prakriti.vata,
                "pitta": prakriti.pitta,
                "kapha": prakriti.kapha,
                "dominant": prakriti.dominant,
                "confidence": prakriti.confidence,
                "provisional": prakriti.provisional,
                "items_answered": prakriti.items_answered,
                "items_total": prakriti.items_total,
                "provenance": list(prakriti.provenance),
            }
        }

        if summary.ayush.vikriti is not None:
            result["vikriti"] = summary.ayush.vikriti

        if summary.ayush.agni is not None:
            result["agni"] = summary.ayush.agni

        if summary.ayush.koshtha is not None:
            result["koshtha"] = summary.ayush.koshtha

        if summary.ayush.ahara_vihara:
            result["ahara_vihara"] = list(
                summary.ayush.ahara_vihara
            )

        codes = summary.ayush.codes

        if any(
            value is not None
            for value in codes.values()
        ):
            result["codes"] = dict(codes)

        return result

    @staticmethod
    def _render_delta(
        summary: ClinicalSummary,
    ) -> list[str]:
        delta = summary.delta

        if not delta.is_return_visit:
            return []

        result: list[str] = []

        if delta.visit_number is not None:
            result.append(
                f"Visit number: {delta.visit_number}"
            )

        for change in delta.changed:
            if isinstance(change, str) and change.strip():
                result.append(change.strip())

        if delta.adherence_estimate is not None:
            result.append(
                "Adherence estimate: "
                f"{delta.adherence_estimate:.0f}% "
                "(estimate, not a confirmed fact)"
            )

        return result
