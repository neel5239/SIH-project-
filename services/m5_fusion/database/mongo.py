from __future__ import annotations

import os

from pymongo import MongoClient
from pymongo.database import Database


MONGODB_URI = os.getenv(
    "MEDISAARTHI_MONGODB_URI",
    "mongodb://localhost:27017",
)

DATABASE_NAME = os.getenv(
    "MEDISAARTHI_DB_NAME",
    "medisaarthi",
)


class MongoDatabase:
    """
    Central MongoDB connection for MediSaarthi.

    Default database:
        medisaarthi

    Collections are created automatically by MongoDB
    when the first document is inserted.
    """

    def __init__(self) -> None:
        self.client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=3000,
        )

        self.db: Database = self.client[DATABASE_NAME]

    def ping(self) -> bool:
        self.client.admin.command("ping")
        return True

    @property
    def summaries(self):
        return self.db["summaries"]

    @property
    def provenance(self):
        return self.db["provenance"]

    @property
    def corrections(self):
        return self.db["corrections"]

    @property
    def guardian_log(self):
        return self.db["guardian_log"]

    @property
    def prakriti_scores(self):
        return self.db["prakriti_scores"]


mongo = MongoDatabase()
