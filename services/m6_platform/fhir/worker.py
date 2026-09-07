from datetime import datetime, timezone
from uuid import UUID

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..settings import settings
from ..db.models import OutboxRow
from ..metrics.service import metrics
from ..queue.celery_app import celery


engine = create_engine(settings.database_url)


def is_offline():
    try:
        client = redis.from_url(settings.redis_url)
        value = client.get("purva:offline")

        if value is None:
            return False

        return value.decode().lower() == "true"

    except Exception:
        # If Redis itself is unavailable, fail closed for FHIR delivery.
        return True


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 4},
)
def process_fhir_outbox(self, outbox_id):
    db = Session(engine)

    try:
        row = db.get(OutboxRow, UUID(str(outbox_id)))

        if not row:
            raise ValueError("Outbox item not found")

        if row.status == "sent":
            return {
                "outbox_id": str(row.outbox_id),
                "status": "sent",
            }

        if is_offline():
            row.status = "queued"
            row.last_error = "FHIR delivery paused: platform offline"
            db.commit()

            return {
                "outbox_id": str(row.outbox_id),
                "status": "queued",
                "offline": True,
            }

        row.status = "processing"
        row.attempts += 1
        row.last_error = None
        db.commit()

        # PURVA_MOCK transport.
        #
        # This is deliberately deterministic for the local M6 demo.
        # A real ABDM/FHIR HTTP transport can replace this block later.
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc)
        row.last_error = None

        db.commit()

        metrics.fhir_push_total += 1

        return {
            "outbox_id": str(row.outbox_id),
            "status": "sent",
        }

    except Exception as exc:
        db.rollback()

        row = db.get(OutboxRow, UUID(str(outbox_id)))

        if row:
            row.status = "failed"
            row.last_error = str(exc)
            db.commit()

        raise

    finally:
        db.close()
