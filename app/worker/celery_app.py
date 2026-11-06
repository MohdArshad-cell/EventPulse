import os
from celery import Celery
from app.config import settings

celery = Celery(
    "eventpulse",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"]
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # High-reliability task settings
    task_acks_late=True,             # Acknowledge task ONLY after execution finishes
    worker_prefetch_multiplier=1,    # Prevent greedy task buffering by workers
    task_reject_on_worker_lost=True, # Re-queue task if worker crashes unexpectedly
    # Prevent long blocking retries when Redis is not available
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    broker_transport_options={
        "max_retries": 1,
        "interval_start": 0.1,
        "interval_step": 0.2,
        "interval_max": 0.5,
    }
)

# Optional periodic tasks with Celery Beat
celery.conf.beat_schedule = {
    "circuit-breaker-recovery-sweep": {
        "task": "app.worker.tasks.circuit_breaker_sweep",
        "schedule": 60.0,
    },
}
