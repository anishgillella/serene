"""
Celery application configuration.

Broker: redis://localhost:6380/1  (separate DB from cache)
Result backend: redis://localhost:6380/2

Usage:
    celery -A app.celery_app worker --loglevel=info --beat
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings


celery_app = Celery(
    "serene",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Route tasks to different queues
    task_routes={
        "app.tasks.analysis_tasks.*": {"queue": "analysis"},
        "app.tasks.digest_tasks.*": {"queue": "digest"},
        "app.tasks.alert_tasks.*": {"queue": "alerts"},
    },
    # Celery Beat schedule
    beat_schedule={
        "weekly-digest": {
            "task": "app.tasks.digest_tasks.generate_all_digests",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM UTC
        },
        "check-cool-down-reminders": {
            "task": "app.tasks.alert_tasks.check_cool_down_reminders",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        "check-periodic-checkins": {
            "task": "app.tasks.alert_tasks.check_periodic_checkins",
            "schedule": crontab(hour=18, minute=0),  # Daily at 6 PM UTC
        },
    },
)

# Auto-discover tasks from these modules
celery_app.autodiscover_tasks(["app.tasks"])
