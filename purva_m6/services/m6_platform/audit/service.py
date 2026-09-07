from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..db.models import AuditRow

def audit(
    db: Session,
    event_type: str,
    actor_id: str | None = None,
    resource_id: str | None = None,
    session_id=None,
    metadata: dict | None = None,
):
    row = AuditRow(
        event_id=uuid4(),
        event_type=event_type,
        actor_id=actor_id,
        resource_id=resource_id,
        session_id=session_id,
        metadata_json=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
