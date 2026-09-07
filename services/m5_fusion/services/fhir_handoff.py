from __future__ import annotations

from typing import Any


class FHIRHandoff:
    """Builds a deterministic FHIR R4-style handoff bundle.

    This does not diagnose or invent clinical facts.
    """

    def build(self, summary: Any) -> dict[str, Any]:
        resources = [
            {
                "resourceType": "Patient",
                "id": summary.session_id,
            },
            {
                "resourceType": "Encounter",
                "id": summary.summary_id,
                "status": "finished",
            },
        ]

        for section, items in summary.sections.items():
            for index, item in enumerate(items):
                resources.append(
                    {
                        "resourceType": "Observation",
                        "id": f"{summary.summary_id}-{section}-{index}",
                        "status": "final",
                        "code": {
                            "text": section,
                        },
                        "valueString": item.text,
                        "extension": [
                            {
                                "url": "https://medisaarthi.local/provenance",
                                "valueString": prov,
                            }
                            for prov in item.provenance
                        ],
                    }
                )

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": resource}
                for resource in resources
            ],
        }
