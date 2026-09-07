from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from ..db.models import OutboxRow, SessionRow, SummaryRow


def build_fhir_bundle(
    db: Session,
    session_id,
):
    session = db.get(SessionRow, session_id)

    if not session:
        raise ValueError("Session not found")

    summary = (
        db.query(SummaryRow)
        .filter(SummaryRow.session_id == session_id)
        .order_by(SummaryRow.generated_at.desc())
        .first()
    )

    if not summary:
        raise ValueError("Clinical summary not found")

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": str(session.patient_ref)
                    if session.patient_ref
                    else "local-patient",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": str(session.session_id),
                    "status": "finished"
                    if session.state == "complete"
                    else "in-progress",
                    "class": {
                        "code": session.opd_type,
                    },
                }
            },
            {
                "resource": {
                    "resourceType": "ClinicalImpression",
                    "id": str(summary.summary_id),
                    "status": "completed",
                    "description": "PURVA Clinical Summary",
                    "summary": summary.payload,
                }
            },
        ],
    }


def create_outbox_entry(
    db: Session,
    session_id,
    bundle: dict,
):
    existing = (
        db.query(OutboxRow)
        .filter(
            OutboxRow.session_id == session_id,
            OutboxRow.resource_type == "Bundle",
            OutboxRow.status.in_(["queued", "processing", "sent"]),
        )
        .order_by(OutboxRow.created_at.desc())
        .first()
    )

    if existing:
        return existing

    row = OutboxRow(
        outbox_id=uuid4(),
        session_id=session_id,
        resource_type="Bundle",
        payload=bundle,
        status="queued",
        attempts=0,
        last_error=None,
        created_at=datetime.now(timezone.utc),
        sent_at=None,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return row
