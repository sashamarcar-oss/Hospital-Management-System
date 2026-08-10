from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.appointments.models import Appointment


@shared_task
def send_appointment_reminders():
    """Queue reminders for appointments happening tomorrow."""
    from apps.core.services import notify

    tomorrow = timezone.now().date() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=[Appointment.STATUS_SCHEDULED, Appointment.STATUS_CONFIRMED],
    ).select_related("patient", "patient__user")
    for appointment in appointments:
        if appointment.patient.user:
            notify(
                appointment.patient.user,
                "Appointment reminder",
                f"You have an appointment tomorrow at {appointment.start_time:%H:%M}.",
                notification_type="appointment",
                link="/portal",
            )
    return f"{appointments.count()} reminders queued"
