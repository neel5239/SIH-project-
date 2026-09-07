from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import TriageRow
from ..auth.service import require_roles
from ..triage.manager import events
from ..metrics.service import metrics

router = APIRouter(prefix="/triage", tags=["triage"])

@router.get("/queue")
def queue(db: Session = Depends(get_db), user=Depends(require_roles("nurse","physician","admin"))):
    rows = db.query(TriageRow).filter(TriageRow.status == "waiting").order_by(TriageRow.priority, TriageRow.token_number).all()
    return {"items": [
        {"entry_id": str(r.entry_id), "session_id": str(r.session_id),
         "token_number": r.token_number, "priority": r.priority,
         "reason": r.reason, "rule_id": r.rule_id, "status": r.status}
        for r in rows
    ]}

@router.post("/red-flag")
async def red_flag(
    session_id: UUID, token_number: int, reason: str,
    rule_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles("nurse","physician","admin")),
):
    entry = TriageRow(
        entry_id=uuid4(), session_id=session_id,
        token_number=token_number, priority=0,
        reason=reason, rule_id=rule_id,
        status="waiting",
        entered_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    metrics.red_flags_fired += 1
    await events.publish({
        "event": "red_flag",
        "entry": {
            "entry_id": str(entry.entry_id),
            "session_id": str(session_id),
            "token_number": token_number,
            "priority": 0,
            "reason": reason,
            "rule_id": rule_id,
        }
    })
    return {"entry_id": str(entry.entry_id), "status": "queued"}

@router.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    q = await events.subscribe()
    try:
        while True:
            event = await q.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        events.unsubscribe(q)
    except Exception:
        events.unsubscribe(q)
