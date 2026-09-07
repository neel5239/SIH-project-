from datetime import datetime, timezone
from uuid import uuid4, UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .celery_app import celery
from ..settings import settings
from ..db.models import JobRow, SummaryRow
from contracts.models import ClinicalSummary


engine = create_engine(settings.database_url)


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 4},
)
def process_job(self, job_id, job_type, session_id, payload):
    db = Session(engine)

    try:
        job = db.get(JobRow, UUID(job_id))

        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        db.commit()

        if job_type == "clinical_summary":
            if not session_id:
                raise ValueError("session_id is required")

            summary_id = uuid4()
            generated_at = datetime.now(timezone.utc)

            summary = ClinicalSummary(
                summary_id=summary_id,
                session_id=UUID(session_id),
                status="draft",
                sections=payload.get(
                    "sections",
                    {
                        "chief_complaint": [],
                        "history": [],
                        "examination": [],
                        "assessment": [],
                        "plan": [],
                    },
                ),
                ayush=payload.get("ayush"),
                timeline=payload.get("timeline", []),
                delta=payload.get("delta"),
                alerts=payload.get("alerts", []),
                guardian=payload.get(
                    "guardian",
                    {
                        "status": "not_evaluated",
                        "message": "PURVA_MOCK clinical summary",
                    },
                ),
                generated_at=generated_at,
            )

            row = SummaryRow(
                summary_id=summary.summary_id,
                session_id=summary.session_id,
                status=summary.status,
                payload=summary.model_dump(mode="json"),
                generated_at=summary.generated_at,
            )

            db.add(row)

        elif job_type not in {
            "ocr",
            "fhir_push",
            "tts",
        }:
            raise ValueError(f"Unsupported job type: {job_type}")

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.last_error = None
        db.commit()

        return {
            "job_id": job_id,
            "job_type": job_type,
            "status": "completed",
        }

    except Exception as exc:
        db.rollback()

        job = db.get(JobRow, UUID(job_id))
        if job:
            job.status = "failed"
            job.last_error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()

        raise

    finally:
        db.close()
