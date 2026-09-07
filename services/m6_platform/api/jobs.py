from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import JobRow
from ..auth.service import require_roles
from ..queue.tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobRequest(BaseModel):
    type: str
    session_id: UUID | None = None
    payload: dict = {}


@router.post("", status_code=202)
def submit_job(
    body: JobRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "physician", "nurse")),
):
    if body.type == "clinical_summary" and body.session_id is None:
        raise HTTPException(
            400,
            "session_id is required for clinical_summary jobs",
        )

    jid = uuid4()
    now = datetime.now(timezone.utc)

    row = JobRow(
        job_id=jid,
        type=body.type,
        session_id=body.session_id,
        payload=body.payload,
        status="queued",
        attempts=0,
        max_attempts=5,
        created_at=now,
    )

    db.add(row)
    db.commit()

    process_job.delay(
        str(jid),
        body.type,
        str(body.session_id) if body.session_id else None,
        body.payload,
    )

    return {
        "job_id": str(jid),
        "status": "queued",
        "poll_url": f"/api/v1/jobs/{jid}",
    }


@router.get("/{job_id}")
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "physician", "nurse")),
):
    row = db.get(JobRow, job_id)

    if not row:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": str(row.job_id),
        "status": row.status,
        "attempts": row.attempts,
        "last_error": row.last_error,
        "created_at": row.created_at.isoformat(),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }
