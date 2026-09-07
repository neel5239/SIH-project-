from typing import Any
from services.m5_fusion.database.mongo import mongo


class PrakritiRepository:
    def save(self, record: dict[str, Any]) -> None:
        summary_id = str(record["summary_id"])
        document = dict(record)
        document["_id"] = summary_id
        mongo.prakriti_scores.replace_one(
            {"_id": summary_id},
            document,
            upsert=True,
        )

    def get(self, summary_id: str) -> dict[str, Any] | None:
        return mongo.prakriti_scores.find_one(
            {"_id": str(summary_id)},
            {"_id": 0},
        )
