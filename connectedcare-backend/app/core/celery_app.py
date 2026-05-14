import os
from celery import Celery

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")


def make_celery(app_name: str = "connectedcare") -> Celery:
    celery = Celery(
        app_name,
        broker=REDIS_URL,
        backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
    )
    # production-grade defaults
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
    )
    return celery


celery_app = make_celery()

__all__ = ["celery_app"]
