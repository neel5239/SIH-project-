from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.service import require_roles
from ..db.session import get_db
from ..db.models import OutboxRow
from ..audit.service import audit
from ..fhir.service import build_fhir_bundle, create_outbox_entry
from ..fhir.worker import process_fhir_outbox


router = APIRouter(tags=["fhir"])


@router.get("/session/{session_id}/fhir")
def get_fhir(
    session_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "admin")),
):
    try:
        bundle = build_fhir_bundle(db, session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    audit(
        db,
        "fhir_bundle_viewed",
        actor_id=user["user_id"],
        resource_id=str(session_id),
        session_id=session_id,
    )

    return bundle


@router.post("/session/{session_id}/fhir/push")
def push_fhir(
    session_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "admin")),
):
    try:
        bundle = build_fhir_bundle(db, session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    row = create_outbox_entry(
        db,
        session_id,
        bundle,
    )

    process_fhir_outbox.delay(str(row.outbox_id))

    audit(
        db,
        "fhir_push_queued",
        actor_id=user["user_id"],
        resource_id=str(row.outbox_id),
        session_id=session_id,
    )

    return {
        "bundle_id": str(row.outbox_id),
        "status": "queued",
    }


@router.get("/fhir/outbox")
def list_outbox(
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    rows = (
        db.query(OutboxRow)
        .order_by(OutboxRow.created_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "outbox_id": str(row.outbox_id),
                "session_id": (
                    str(row.session_id)
                    if row.session_id
                    else None
                ),
                "resource_type": row.resource_type,
                "status": row.status,
                "attempts": row.attempts,
                "last_error": row.last_error,
                "created_at": row.created_at.isoformat(),
                "sent_at": (
                    row.sent_at.isoformat()
                    if row.sent_at
                    else None
                ),
            }
            for row in rows
        ]
    }


@router.post("/fhir/outbox/{outbox_id}/retry")
def retry_outbox(
    outbox_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin")),
):
    row = db.get(OutboxRow, outbox_id)

    if not row:
        raise HTTPException(404, "Outbox item not found")

    if row.status == "sent":
        raise HTTPException(
            409,
            "Outbox item has already been sent",
        )

    row.status = "queued"
    row.last_error = None

    db.commit()

    process_fhir_outbox.delay(str(row.outbox_id))

    audit(
        db,
        "fhir_push_retry_queued",
        actor_id=user["user_id"],
        resource_id=str(row.outbox_id),
        session_id=row.session_id,
    )

    return {
        "outbox_id": str(row.outbox_id),
        "status": "queued",
    }
