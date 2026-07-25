from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "nagrik_ai_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.email_tasks", "app.tasks.priority_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # BMC/Mumbai only operates in this timezone, so "2 AM" in the beat
    # schedule below means 2 AM IST, not UTC.
    timezone="Asia/Kolkata",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "nightly-priority-rescore": {
        "task": "rescore_all_complaints_task",
        "schedule": crontab(hour=2, minute=0),
    },
}
