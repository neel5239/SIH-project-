from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


ALLOWED_SECTIONS = (
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


@dataclass(frozen=True)
class GeneratedItem:
    text: str
    provenance: tuple[str, ...]
    answered_by: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "provenance": list(self.provenance),
            "answered_by": self.answered_by,
        }


class SchemaGenerationError(ValueError):
    """Raised when a generated item violates the M5 schema."""


class SchemaConstrainedGenerator:
    """
    Deterministic Phase 2 generator.

    This component does not diagnose, infer causation, estimate likelihood,
    or recommend treatment. It only renders already-sourced facts.

    Safety properties:
    - fixed section allow-list
    - provenance is mandatory
    - empty/invalid provenance is rejected
    - no arbitrary section names
    - deterministic output
    - no free-form model-generated clinical content
    """

    def generate(
        self,
        *,
        sections: Mapping[str, Iterable[Mapping[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:
        output: dict[str, list[dict[str, Any]]] = {
            section: []
            for section in ALLOWED_SECTIONS
        }

        for section, items in sections.items():
            if section not in ALLOWED_SECTIONS:
                raise SchemaGenerationError(
                    f"Unsupported clinical section: {section}"
                )

            for item in items:
                generated = self._render_item(item)
                output[section].append(generated.to_dict())

        return output

    def _render_item(
        self,
        item: Mapping[str, Any],
    ) -> GeneratedItem:
        text = item.get("text")

        if not isinstance(text, str) or not text.strip():
            raise SchemaGenerationError(
                "Generated clinical item requires non-empty text"
            )

        raw_provenance = item.get("provenance")

        if not isinstance(raw_provenance, (list, tuple)):
            raise SchemaGenerationError(
                "Generated clinical item requires provenance"
            )

        provenance = tuple(
            str(ref).strip()
            for ref in raw_provenance
            if str(ref).strip()
        )

        if not provenance:
            raise SchemaGenerationError(
                "Generated clinical item requires at least one provenance reference"
            )

        answered_by = item.get("answered_by", "unknown")

        if answered_by not in {"self", "proxy", "unknown"}:
            answered_by = "unknown"

        return GeneratedItem(
            text=text.strip(),
            provenance=provenance,
            answered_by=answered_by,
        )

    @staticmethod
    def template_from_summary_item(
        text: str,
        provenance: list[str],
        answered_by: str = "unknown",
    ) -> GeneratedItem:
        """
        Deterministic template fallback.

        Used when a future model-based generator fails. The fallback
        does not invent any clinical content.
        """
        return GeneratedItem(
            text=text.strip(),
            provenance=tuple(
                ref.strip()
                for ref in provenance
                if ref and ref.strip()
            ),
            answered_by=(
                answered_by
                if answered_by in {"self", "proxy", "unknown"}
                else "unknown"
            ),
        )
