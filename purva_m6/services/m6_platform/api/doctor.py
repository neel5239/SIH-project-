from copy import deepcopy
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import SummaryRow, CorrectionRow, SessionRow
from ..auth.service import require_roles
from ..audit.service import audit
from ..fhir.service import build_fhir_bundle, create_outbox_entry
from ..fhir.worker import process_fhir_outbox


router = APIRouter(prefix="/doctor", tags=["doctor"])


class EditRequest(BaseModel):
    field_path: str
    corrected_value: str


def set_path(obj, path, value):
    parts = path.split(".")
    current = obj

    for part in parts[:-1]:
        if "[" in part:
            name, index = part[:-1].split("[")
            current = current[name][int(index)]
        else:
            current = current[part]

    final = parts[-1]

    if "[" in final:
        name, index = final[:-1].split("[")
        current[name][int(index)] = value
    else:
        current[final] = value


@router.get("/queue")
def queue(
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "nurse", "admin")),
):
    rows = (
        db.query(SummaryRow)
        .order_by(SummaryRow.generated_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "session_id": str(r.session_id),
                "summary_id": str(r.summary_id),
                "status": r.status,
            }
            for r in rows
        ]
    }


@router.get("/session/{session_id}/summary")
def summary(
    session_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "nurse", "admin")),
):
    row = (
        db.query(SummaryRow)
        .filter(SummaryRow.session_id == session_id)
        .order_by(SummaryRow.generated_at.desc())
        .first()
    )

    if not row:
        raise HTTPException(404, "Summary not found")

    audit(
        db,
        "summary_viewed",
        actor_id=user["user_id"],
        resource_id=str(row.summary_id),
        session_id=row.session_id,
    )

    return row.payload


@router.patch("/summary/{summary_id}/field")
def edit(
    summary_id: UUID,
    body: EditRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "admin")),
):
    row = db.get(SummaryRow, summary_id)

    if not row:
        raise HTTPException(404, "Summary not found")

    if row.status == "signed":
        raise HTTPException(
            status_code=409,
            detail="Signed summaries cannot be edited",
        )

    payload = deepcopy(row.payload)

    try:
        current = payload

        for part in body.field_path.split("."):
            if "[" in part:
                name, index = part[:-1].split("[")
                current = current[name][int(index)]
            else:
                current = current[part]

        generated = str(current)

        set_path(
            payload,
            body.field_path,
            body.corrected_value,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid field_path",
        ) from exc

    correction = CorrectionRow(
        correction_id=uuid4(),
        summary_id=row.summary_id,
        section=(
            body.field_path.split(".")[1]
            if "." in body.field_path
            else body.field_path
        ),
        field_path=body.field_path,
        generated_value=generated,
        corrected_value=body.corrected_value,
        source_module="M5",
        source_prov_id=None,
        corrected_by=user["user_id"],
        corrected_at=datetime.now(timezone.utc),
    )

    payload["status"] = "edited"

    row.payload = payload
    row.status = "edited"

    db.add(correction)
    db.commit()
    db.refresh(row)

    audit(
        db,
        "summary_field_corrected",
        actor_id=user["user_id"],
        resource_id=str(row.summary_id),
        session_id=row.session_id,
        metadata={
            "field_path": body.field_path,
            "correction_id": str(correction.correction_id),
        },
    )

    return {
        "updated": True,
        "correction_id": str(correction.correction_id),
    }


@router.post("/summary/{summary_id}/sign")
def sign(
    summary_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("physician", "admin")),
):
    row = db.get(SummaryRow, summary_id)

    if not row:
        raise HTTPException(404, "Summary not found")

    if row.status == "signed":
        raise HTTPException(
            status_code=409,
            detail="Summary is already signed",
        )

    session = db.get(SessionRow, row.session_id)

    if not session:
        raise HTTPException(404, "Session not found")

    now = datetime.now(timezone.utc)

    row.status = "signed"

    payload = deepcopy(row.payload)
    payload["status"] = "signed"
    row.payload = payload

    # A physician signing the final clinical summary completes the session.
    session.state = "complete"

    db.commit()
    db.refresh(row)
    db.refresh(session)

    # Build the FHIR Bundle from the newly signed summary.
    bundle = build_fhir_bundle(db, row.session_id)

    # Create or reuse the session's FHIR outbox entry.
    outbox = create_outbox_entry(
        db,
        row.session_id,
        bundle,
    )

    # Queue delivery. The worker will respect offline mode.
    process_fhir_outbox.delay(str(outbox.outbox_id))

    audit(
        db,
        "summary_signed",
        actor_id=user["user_id"],
        resource_id=str(summary_id),
        session_id=row.session_id,
        metadata={
            "session_state": "complete",
            "completed_at": now.isoformat(),
            "fhir_outbox_id": str(outbox.outbox_id),
        },
    )

    return {
        "status": "signed",
        "summary_id": str(summary_id),
        "session_state": "complete",
        "fhir_push": "queued",
        "outbox_id": str(outbox.outbox_id),
    }
