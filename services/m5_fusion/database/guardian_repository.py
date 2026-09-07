from typing import Any
from services.m5_fusion.database.mongo import mongo


class GuardianLogRepository:
    def save(self, record: dict[str, Any]) -> None:
        document = dict(record)
        mongo.guardian_log.insert_one(document)

    def list_for_summary(self, summary_id: str) -> list[dict[str, Any]]:
        return list(
            mongo.guardian_log.find(
                {"summary_id": summary_id},
                {"_id": 0},
            )
        )

    def count(self) -> int:
        return mongo.guardian_log.count_documents({})
