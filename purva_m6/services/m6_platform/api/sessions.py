from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import SessionRow, ConsentRow
from ..auth.service import kiosk_auth
from ..storage.redis import set_session, delete_session
from ..audit.service import audit

router = APIRouter(prefix="/session", tags=["session"])


class CreateSessionRequest(BaseModel):
    language: str = "hi"
    opd_type: str = Field(default="allopathic", pattern="^(allopathic|ayush)$")
    token_number: int = 47
    kiosk_id: str = "AIIA-OPD-K03"
    abha_id: str | None = None
    is_return_visit: bool = False
    previous_encounter_id: UUID | None = None


class ConsentRequest(BaseModel):
    consent_version: str = "2.1"
    consent_text_hash: str
    permissions: dict
    assent_method: str = Field(pattern="^(voice|touch)$")


def resolve_patient_ref(abha_id: str | None) -> UUID | None:
    if not abha_id:
        return None

    import uuid

    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"purva:patient:{abha_id}",
    )


@router.post("", dependencies=[Depends(kiosk_auth)])
def create_session(
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
):
    sid, cid = uuid4(), uuid4()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=2)

    patient_ref = resolve_patient_ref(body.abha_id)

    row = SessionRow(
        session_id=sid,
        abha_id=body.abha_id,
        patient_ref=patient_ref,
        language=body.language,
        opd_type=body.opd_type,
        consent_id=cid,
        token_number=body.token_number,
        kiosk_id=body.kiosk_id,
        state="created",
        phr_linked=False,
        is_return_visit=body.is_return_visit,
        previous_encounter_id=body.previous_encounter_id,
        started_at=now,
        expires_at=expires,
    )

    db.add(row)
    db.commit()

    set_session(
        str(sid),
        {
            "session_id": str(sid),
            "state": "created",
        },
        ttl=7200,
    )

    audit(
        db,
        "session_created",
        actor_id="kiosk",
        session_id=sid,
        metadata={
            "patient_linked": patient_ref is not None,
            "is_return_visit": body.is_return_visit,
        },
    )

    return {
        "session_id": str(sid),
        "consent_id": str(cid),
        "state": "created",
        "expires_at": expires.isoformat(),
    }


@router.post("/{session_id}/consent", dependencies=[Depends(kiosk_auth)])
def grant_consent(
    session_id: UUID,
    body: ConsentRequest,
    db: Session = Depends(get_db),
):
    row = db.get(SessionRow, session_id)

    if not row:
        raise HTTPException(404, "Session not found")

    if not body.permissions.get("capture", False):
        row.state = "aborted"
        db.commit()
        delete_session(str(session_id))
        raise HTTPException(400, "Capture permission is mandatory")

    now = datetime.now(timezone.utc)

    consent = ConsentRow(
        consent_id=row.consent_id,
        session_id=session_id,
        abha_id=row.abha_id,
        consent_version=body.consent_version,
        language=row.language,
        consent_text_hash=body.consent_text_hash,
        permissions=body.permissions,
        assent_method=body.assent_method,
        assent_audio_blob_id=None,
        operator_present=False,
        granted_at=now,
        expires_at=now + timedelta(hours=2),
    )

    row.state = "consented"

    db.add(consent)
    db.commit()

    set_session(
        str(session_id),
        {
            "session_id": str(session_id),
            "state": "consented",
        },
        ttl=7200,
    )

    audit(
        db,
        "consent_granted",
        actor_id="kiosk",
        session_id=session_id,
    )

    return {
        "session_id": str(session_id),
        "state": "consented",
    }


@router.post("/{session_id}/abort", dependencies=[Depends(kiosk_auth)])
def abort_session(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    row = db.get(SessionRow, session_id)

    if not row:
        raise HTTPException(404, "Session not found")

    row.state = "aborted"
    db.commit()

    delete_session(str(session_id))

    audit(
        db,
        "session_aborted",
        actor_id="kiosk",
        session_id=session_id,
    )

    return {"status": "aborted"}
