from pathlib import Path

path = Path(r".\services\m6_platform\api\admin.py")

text = '''
from fastapi import APIRouter, Depends
import redis
from sqlalchemy import func

from ..settings import settings
from ..auth.service import require_roles
from ..db.session import get_db
from ..db.models import OutboxRow

router = APIRouter(prefix="/admin", tags=["admin"])


def redis_client():
    return redis.from_url(settings.redis_url)


@router.get("/status")
def status(
    db=Depends(get_db),
    user=Depends(require_roles("admin")),
):
    try:
        redis_ok = bool(redis_client().ping())
    except Exception:
        redis_ok = False

    offline_value = redis_client().get("purva:offline")
    offline = bool(
        offline_value and offline_value.decode().lower() == "true"
    )

    queued = (
        db.query(func.count(OutboxRow.outbox_id))
        .filter(OutboxRow.status == "queued")
        .scalar()
        or 0
    )

    failed = (
        db.query(func.count(OutboxRow.outbox_id))
        .filter(OutboxRow.status == "failed")
        .scalar()
        or 0
    )

    return {
        "online": not offline,
        "redis": redis_ok,
        "minio": True,
        "offline_simulation": offline,
        "outbox": {
            "queued": queued,
            "failed": failed,
        },
    }


@router.post("/offline-simulate")
def offline_simulate(
    enabled: bool = True,
    user=Depends(require_roles("admin")),
):
    client = redis_client()

    if enabled:
        client.set("purva:offline", "true")
    else:
        client.delete("purva:offline")

    return {
        "offline": enabled,
        "online": not enabled,
        "message": (
            "Platform marked offline"
            if enabled
            else "Platform marked online"
        ),
    }
'''

path.write_text(text.strip() + "\n", encoding="utf-8")
print("admin.py updated successfully.")
