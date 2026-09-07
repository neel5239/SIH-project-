from datetime import timedelta
from minio import Minio
from ..settings import settings

client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)

BUCKETS = [
    "purva-audio",
    "purva-documents",
    "purva-tts-cache",
    "purva-consent-audio",
]


def ensure_buckets():
    for bucket in BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def check_minio():
    try:
        client.list_buckets()
        return True
    except Exception:
        return False


def put_bytes(bucket, object_name, data, content_type="application/octet-stream"):
    from io import BytesIO

    client.put_object(
        bucket,
        object_name,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def get_bytes(bucket, object_name):
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def signed_url(bucket, object_name, seconds=300):
    return client.presigned_get_object(
        bucket,
        object_name,
        expires=timedelta(seconds=seconds),
    )
