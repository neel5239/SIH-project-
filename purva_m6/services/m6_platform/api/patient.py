from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth.service import require_roles
from ..audit.service import audit
from ..db.models import SessionRow, SummaryRow
from ..db.session import get_db


router = APIRouter(prefix="/patient", tags=["patient"])


def _patient_ref_from_user(user: dict) -> UUID | None:
    """
    Development patient identity bridge.

    Patient JWT subject is expected to contain the same stable patient UUID
    used by SessionRow.patient_ref.
    """
    if user["role"] != "patient":
        return None

    try:
        return UUID(user["user_id"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=403,
            detail="Patient identity is not a valid patient reference",
        )


def _check_patient_access(
    requested_patient_id: UUID,
    user: dict,
):
    if user["role"] in {"physician", "admin"}:
        return

    if user["role"] != "patient":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions",
        )

    own_patient_ref = _patient_ref_from_user(user)

    if own_patient_ref != requested_patient_id:
        raise HTTPException(
            status_code=403,
            detail="Patient access is restricted to the authenticated patient",
        )


def _check_session_access(
    session_row: SessionRow,
    user: dict,
):
    if user["role"] in {"physician", "admin"}:
        return

    if user["role"] != "patient":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions",
        )

    own_patient_ref = _patient_ref_from_user(user)

    if session_row.patient_ref != own_patient_ref:
        raise HTTPException(
            status_code=403,
            detail="Patient access is restricted to the authenticated patient",
        )


def _text_from_section(section: dict | None) -> list[str]:
    if not section:
        return []

    result = []

    if isinstance(section, list):
        for item in section:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    result.append(str(text))
            elif item:
                result.append(str(item))

    return result


@router.get("/{patient_id}/timeline")
def timeline(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("patient", "physician", "admin")),
):
    _check_patient_access(patient_id, user)

    sessions = (
        db.query(SessionRow)
        .filter(SessionRow.patient_ref == patient_id)
        .order_by(SessionRow.started_at.desc())
        .all()
    )

    audit(
        db,
        "patient_timeline_viewed",
        actor_id=user["user_id"],
        resource_id=str(patient_id),
        metadata={"session_count": len(sessions)},
    )

    return {
        "patient_id": str(patient_id),
        "timeline": [
            {
                "session_id": str(s.session_id),
                "started_at": s.started_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
                "state": s.state,
                "language": s.language,
                "opd_type": s.opd_type,
                "token_number": s.token_number,
                "is_return_visit": s.is_return_visit,
                "previous_encounter_id": (
                    str(s.previous_encounter_id)
                    if s.previous_encounter_id
                    else None
                ),
                "phr_linked": s.phr_linked,
            }
            for s in sessions
        ],
    }


@router.get("/session/{session_id}/recap")
def recap(
    session_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_roles("patient", "physician", "admin")),
):
    session_row = db.get(SessionRow, session_id)

    if not session_row:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    _check_session_access(session_row, user)

    summary = (
        db.query(SummaryRow)
        .filter(SummaryRow.session_id == session_id)
        .order_by(SummaryRow.generated_at.desc())
        .first()
    )

    if not summary:
        audit(
            db,
            "patient_recap_viewed",
            actor_id=user["user_id"],
            resource_id=str(session_id),
            session_id=session_id,
            metadata={"status": "not_available"},
        )

        return {
            "status": "not_available",
            "session_id": str(session_id),
        }

    payload = summary.payload or {}
    sections = payload.get("sections") or {}

    chief_complaint = _text_from_section(
        sections.get("chief_complaint")
    )

    history = _text_from_section(
        sections.get("history")
    )

    assessment = _text_from_section(
        sections.get("assessment")
    )

    plan = _text_from_section(
        sections.get("plan")
    )

    recap_parts = []

    if chief_complaint:
        recap_parts.append(
            "मुख्य शिकायत: " + "; ".join(chief_complaint)
        )

    if history:
        recap_parts.append(
            "इतिहास: " + "; ".join(history)
        )

    if assessment:
        recap_parts.append(
            "आकलन: " + "; ".join(assessment)
        )

    if plan:
        recap_parts.append(
            "योजना: " + "; ".join(plan)
        )

    if recap_parts:
        text = "। ".join(recap_parts) + "।"
    else:
        text = "आपकी क्लिनिकल जानकारी डॉक्टर के लिए तैयार की गई है।"

    audit(
        db,
        "patient_recap_viewed",
        actor_id=user["user_id"],
        resource_id=str(summary.summary_id),
        session_id=session_id,
        metadata={"status": "ready"},
    )

    return {
        "status": "ready",
        "session_id": str(session_id),
        "language": session_row.language,
        "text": text,
        "summary_id": str(summary.summary_id),
    }
