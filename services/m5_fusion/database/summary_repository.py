from __future__ import annotations

from datetime import datetime, timezone

from services.m5_fusion.database.mongo import mongo
from services.m5_fusion.models import ClinicalSummary


class SummaryRepository:
    def ping(self) -> bool:
        return mongo.ping()

    def save(self, summary: ClinicalSummary) -> None:
        document = summary.model_dump(mode="json")
        document["updated_at"] = datetime.now(timezone.utc)

        mongo.summaries.replace_one(
            {"session_id": summary.session_id},
            document,
            upsert=True,
        )

    def get(self, session_id: str) -> ClinicalSummary | None:
        document = mongo.summaries.find_one(
            {"session_id": session_id},
            {"_id": 0},
        )

        if document is None:
            return None

        return ClinicalSummary.model_validate(document)

    def get_by_summary_id(self, summary_id: str) -> ClinicalSummary | None:
        document = mongo.summaries.find_one(
            {"summary_id": summary_id},
            {"_id": 0},
        )

        if document is None:
            return None

        return ClinicalSummary.model_validate(document)

    def delete(self, session_id: str) -> bool:
        result = mongo.summaries.delete_one(
            {"session_id": session_id}
        )

        return result.deleted_count == 1

    def exists(self, session_id: str) -> bool:
        return (
            mongo.summaries.count_documents(
                {"session_id": session_id},
                limit=1,
            )
            > 0
        )
