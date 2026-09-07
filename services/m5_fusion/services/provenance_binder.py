from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


VALID_PROVENANCE_KINDS = {
    "audio_offset",
    "image_bbox",
    "physician_entry",
    "transcript",
    "text",
}


@dataclass(frozen=True)
class ProvenanceRecord:
    prov_id: str
    kind: str
    source_ref: str | None = None
    transcript: str | None = None
    retain_audio: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BoundItem:
    text: str
    provenance: tuple[str, ...]
    answered_by: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "provenance": list(self.provenance),
            "answered_by": self.answered_by,
        }


class ProvenanceBinder:
    """
    M5 provenance validation and binding layer.

    Safety rules:
    - An item without valid provenance is silently discarded.
    - Invalid provenance references are never emitted.
    - Duplicate provenance references are removed.
    - Conflicting facts are not resolved here.
    - No clinical content is invented.
    - If retained audio is unavailable, transcript/text provenance
      can remain usable.
    """

    def __init__(
        self,
        provenance_store: Mapping[str, Mapping[str, Any]] | None = None,
    ):
        self.provenance_store = provenance_store or {}
        self.dropped_count = 0

    def bind_and_filter(
        self,
        items: list[Mapping[str, Any]],
    ) -> list[BoundItem]:
        bound: list[BoundItem] = []

        for item in items:
            result = self._bind_item(item)

            if result is None:
                self.dropped_count += 1
                continue

            bound.append(result)

        return bound

    def _bind_item(
        self,
        item: Mapping[str, Any],
    ) -> BoundItem | None:
        text = item.get("text")

        if not isinstance(text, str) or not text.strip():
            return None

        raw_refs = item.get("provenance")

        if not isinstance(raw_refs, (list, tuple)):
            return None

        valid_refs: list[str] = []

        for raw_ref in raw_refs:
            if not isinstance(raw_ref, str):
                continue

            prov_id = raw_ref.strip()

            if not prov_id:
                continue

            record = self.provenance_store.get(prov_id)

            if record is None:
                continue

            if not self._valid_record(record):
                continue

            valid_refs.append(prov_id)

        valid_refs = list(dict.fromkeys(valid_refs))

        if not valid_refs:
            return None

        answered_by = item.get("answered_by", "unknown")

        if answered_by not in {"self", "proxy", "unknown"}:
            answered_by = "unknown"

        return BoundItem(
            text=text.strip(),
            provenance=tuple(valid_refs),
            answered_by=answered_by,
        )

    @staticmethod
    def _valid_record(
        record: Mapping[str, Any],
    ) -> bool:
        prov_id = record.get("prov_id")

        if not isinstance(prov_id, str) or not prov_id.strip():
            return False

        kind = record.get("kind")

        if kind not in VALID_PROVENANCE_KINDS:
            return False

        # Audio provenance is valid even when the raw audio itself
        # is not retained, provided a transcript/text reference exists.
        if kind == "audio_offset":
            retain_audio = record.get("retain_audio", True)

            if retain_audio is False:
                transcript = record.get("transcript")

                if not isinstance(transcript, str) or not transcript.strip():
                    return False

        return True

    def reset_metrics(self) -> None:
        self.dropped_count = 0
