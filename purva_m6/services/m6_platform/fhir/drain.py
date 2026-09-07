from datetime import datetime, timezone

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..settings import settings
from ..db.models import OutboxRow
from ..queue.celery_app import celery
from .worker import process_fhir_outbox


engine = create_engine(settings.database_url)


@celery.task
def drain_fhir_outbox():
    db = Session(engine)

    try:
        client = redis.from_url(settings.redis_url)
        offline = client.get("purva:offline")

        if offline and offline.decode().lower() == "true":
            return {
                "status": "offline",
                "queued": 0,
            }

        rows = (
            db.query(OutboxRow)
            .filter(
                OutboxRow.status.in_(["queued", "failed"])
            )
            .order_by(OutboxRow.created_at.asc())
            .limit(100)
            .all()
        )

        queued = 0

        for row in rows:
            process_fhir_outbox.delay(str(row.outbox_id))
            queued += 1

        return {
            "status": "online",
            "queued": queued,
        }

    finally:
        db.close()
