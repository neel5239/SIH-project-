from time import perf_counter
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import SessionRow
from ..auth.service import kiosk_auth
from ..settings import settings
from ..metrics.service import metrics


router = APIRouter(prefix="/session", tags=["conversation"])


class TurnRequest(BaseModel):
    transcript: str
    input_mode: str = "voice"


@router.post("/{session_id}/turn", dependencies=[Depends(kiosk_auth)])
def turn(
    session_id: UUID,
    body: TurnRequest,
    db: Session = Depends(get_db),
):
    started = perf_counter()

    row = db.get(SessionRow, session_id)

    if not row:
        raise HTTPException(404, "Session not found")

    row.state = "interviewing"
    db.commit()

    # M6 only transports the turn.
    # M3 owns the question/slot logic.
    mock = "m3" in [
        x.strip()
        for x in settings.purva_mock.split(",")
        if x.strip()
    ]

    elapsed_ms = (perf_counter() - started) * 1000
    metrics.record_turn_latency(elapsed_ms)

    return {
        "session_id": str(session_id),
        "accepted": True,
        "mock": mock,
        "next_action": "continue_interview",
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
