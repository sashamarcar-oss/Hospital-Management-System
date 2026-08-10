"""Celery configuration. Gracefully degrades if Redis is unavailable."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("hospital")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-appointment-reminders": {
        "task": "apps.appointments.tasks.send_appointment_reminders",
        "schedule": crontab(minute=0, hour=8),
    },
    "low-stock-alerts": {
        "task": "apps.pharmacy.tasks.low_stock_alerts",
        "schedule": crontab(minute=0, hour=9),
    },
}
