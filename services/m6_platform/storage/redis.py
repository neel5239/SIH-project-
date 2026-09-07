from redis import Redis
from ..settings import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)

def check_redis():
    try:
        return bool(redis_client.ping())
    except Exception:
        return False

def set_session(session_id, data, ttl=7200):
    import json
    redis_client.setex(f"purva:session:{session_id}", ttl, json.dumps(data))

def get_session(session_id):
    import json
    value = redis_client.get(f"purva:session:{session_id}")
    return json.loads(value) if value else None

def delete_session(session_id):
    redis_client.delete(f"purva:session:{session_id}")
