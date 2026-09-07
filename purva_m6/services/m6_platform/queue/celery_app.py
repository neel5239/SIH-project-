from celery import Celery
from celery.schedules import crontab

from ..settings import settings


celery = Celery(
    "purva_m6",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "services.m6_platform.queue.tasks",
        "services.m6_platform.fhir.worker",
        "services.m6_platform.fhir.drain",
    ],
)

celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "drain-fhir-outbox-every-15-seconds": {
            "task": "services.m6_platform.fhir.drain.drain_fhir_outbox",
            "schedule": 15.0,
        },
    },
)
