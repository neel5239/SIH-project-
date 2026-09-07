from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from services.m5_fusion.database.correction_repository import (
    CorrectionRepository,
)


class CorrectionService:
    def __init__(self, repository: CorrectionRepository | None = None):
        self.repository = repository or CorrectionRepository()

    def capture(
        self,
        *,
        summary_id: str,
        section: str,
        field_path: str,
        corrected_value: Any,
        physician_id: str,
        generated_value: Any = None,
        source_module: str = "m5_fusion",
        provenance: list[str] | None = None,
    ) -> dict[str, Any]:
        record = {
            "correction_id": str(uuid4()),
            "summary_id": summary_id,
            "section": section,
            "field_path": field_path,
            "generated_value": generated_value,
            "corrected_value": corrected_value,
            "source_module": source_module,
            "provenance": provenance or [],
            "physician_id": physician_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repository.save(record)
        return record

    def accuracy(self, window: str = "7d") -> dict[str, Any]:
        records = self.repository.count()

        if records == 0:
            return {
                "window": window,
                "status": "no_corrections",
                "corrections": 0,
                "accuracy": None,
            }

        all_records = list(
            __import__(
                "services.m5_fusion.database.mongo",
                fromlist=["mongo"],
            ).mongo.corrections.find({}, {"_id": 0})
        )

        unchanged = sum(
            1
            for record in all_records
            if record.get("generated_value")
            == record.get("corrected_value")
        )

        return {
            "window": window,
            "status": "available",
            "corrections": records,
            "unchanged": unchanged,
            "accuracy": round(unchanged / records, 4),
        }
