from fastapi import APIRouter
from ..db.session import engine
from ..storage.redis import check_redis
from ..storage.minio import check_minio
from ..llm.runtime import LLMRuntime
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@router.get("/health/deps")
async def deps():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        postgres = True
    except Exception:
        postgres = False
    return {
        "postgres": postgres,
        "redis": check_redis(),
        "minio": check_minio(),
        "llm": await LLMRuntime().health(),
    }

@router.get("/ready")
async def ready():
    d = await deps()
    ok = all(d.values())
    return {"status": "ready" if ok else "not_ready", "dependencies": d}
