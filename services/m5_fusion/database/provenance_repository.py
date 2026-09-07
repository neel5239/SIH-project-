from __future__ import annotations

from typing import Any

from services.m5_fusion.database.mongo import mongo


class ProvenanceRepository:
    """
    Persistent MongoDB repository for M5 provenance records.

    Provenance is referenced by prov_id. Raw audio/image payloads are
    not stored here; this repository stores provenance metadata/references.
    """

    def save(
        self,
        record: dict[str, Any],
    ) -> None:
        prov_id = record.get("prov_id")

        if not prov_id:
            raise ValueError("Provenance record requires prov_id")

        document = dict(record)
        document["_id"] = str(prov_id)

        mongo.provenance.replace_one(
            {"_id": str(prov_id)},
            document,
            upsert=True,
        )

    def get(
        self,
        prov_id: str,
    ) -> dict[str, Any] | None:
        document = mongo.provenance.find_one(
            {"_id": str(prov_id)},
            {"_id": 0},
        )

        return document

    def exists(
        self,
        prov_id: str,
    ) -> bool:
        return (
            mongo.provenance.count_documents(
                {"_id": str(prov_id)},
                limit=1,
            )
            > 0
        )

    def delete(
        self,
        prov_id: str,
    ) -> bool:
        result = mongo.provenance.delete_one(
            {"_id": str(prov_id)}
        )

        return result.deleted_count == 1
