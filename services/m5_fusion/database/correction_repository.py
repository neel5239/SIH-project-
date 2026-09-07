from typing import Any
from services.m5_fusion.database.mongo import mongo


class CorrectionRepository:
    def save(self, record: dict[str, Any]) -> None:
        correction_id = str(record["correction_id"])
        document = dict(record)
        document["_id"] = correction_id
        mongo.corrections.replace_one(
            {"_id": correction_id},
            document,
            upsert=True,
        )

    def list_for_summary(self, summary_id: str) -> list[dict[str, Any]]:
        return list(
            mongo.corrections.find(
                {"summary_id": summary_id},
                {"_id": 0},
            )
        )

    def count(self) -> int:
        return mongo.corrections.count_documents({})
