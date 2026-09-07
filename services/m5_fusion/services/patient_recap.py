from __future__ import annotations

from typing import Any


class PatientRecapService:
    def build(self, summary: Any, language: str = "en") -> dict[str, Any]:
        sections: dict[str, list[str]] = {}

        for section, items in summary.sections.items():
            values = []
            for item in items:
                values.append(item.text)
            if values:
                sections[section] = values

        return {
            "language": language,
            "summary_id": summary.summary_id,
            "mode": "template",
            "sections": sections,
            "ayush": (
                summary.ayush.model_dump(mode="json")
                if summary.ayush is not None
                else None
            ),
            "safety": {
                "diagnosis_generated": False,
                "treatment_recommendation_generated": False,
            },
        }
