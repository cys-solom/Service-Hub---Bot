"""Celery app configuration"""
from celery import Celery
from celery.schedules import crontab

app = Celery(
    "diaastore",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
    include=[
        "workers.tasks.payment_tasks",
        "workers.tasks.stock_tasks",
        "workers.tasks.backup_tasks",
        "workers.tasks.notification_tasks",
        "workers.tasks.provider_tasks",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=300,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule — periodic tasks
app.conf.beat_schedule = {
    "check-expired-payments": {
        "task": "workers.tasks.payment_tasks.check_expired_payments",
        "schedule": 60.0,  # Every 60 seconds
    },
    "sync-provider-stock": {
        "task": "workers.tasks.provider_tasks.sync_all_providers",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "daily-backup": {
        "task": "workers.tasks.backup_tasks.create_daily_backup",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "cleanup-old-logs": {
        "task": "workers.tasks.backup_tasks.cleanup_old_logs",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    "check-low-stock": {
        "task": "workers.tasks.stock_tasks.check_low_stock_alerts",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
}
