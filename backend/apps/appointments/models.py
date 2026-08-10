from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Appointment(BaseModel):
    STATUS_SCHEDULED = "scheduled"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CHECKED_IN, "Checked In"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_NO_SHOW, "No-Show"),
    ]

    PRIORITY_ROUTINE = "routine"
    PRIORITY_URGENT = "urgent"
    PRIORITY_EMERGENCY = "emergency"

    PRIORITY_CHOICES = [
        (PRIORITY_ROUTINE, "Routine"),
        (PRIORITY_URGENT, "Urgent"),
        (PRIORITY_EMERGENCY, "Emergency"),
    ]

    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE, related_name="appointments"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments",
        limit_choices_to={"role__code__in": ["doctor", "admin"]},
    )
    department = models.ForeignKey(
        "departments.Department", on_delete=models.CASCADE, related_name="appointments"
    )
    appointment_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.TextField(blank=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_ROUTINE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    notes = models.TextField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["appointment_date", "start_time"]
        indexes = [
            models.Index(fields=["appointment_date", "doctor"]),
            models.Index(fields=["status", "appointment_date"]),
        ]

    def __str__(self):
        return f"{self.patient} @ {self.appointment_date} {self.start_time:%H:%M}"

    @property
    def display_time(self):
        return f"{self.start_time:%H:%M} - {self.end_time:%H:%M}"


class Queue(BaseModel):
    """Department/doctor queue built from checked-in appointments."""

    STATUS_WAITING = "waiting"
    STATUS_IN_CONSULTATION = "in_consultation"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_WAITING, "Waiting"),
        (STATUS_IN_CONSULTATION, "In Consultation"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="queue_entries")
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="queue_entries"
    )
    department = models.ForeignKey("departments.Department", on_delete=models.CASCADE, related_name="queues")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="queues"
    )
    queue_number = models.CharField(max_length=32, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_WAITING)
    priority = models.CharField(max_length=16, choices=Appointment.PRIORITY_CHOICES, default=Appointment.PRIORITY_ROUTINE)
    checked_in_at = models.DateTimeField(default=timezone.now)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority", "checked_in_at", "id"]
        indexes = [models.Index(fields=["department", "status"])]

    def __str__(self):
        return f"{self.queue_number} - {self.patient} ({self.status})"

    @property
    def waiting_minutes(self):
        if self.checked_in_at and not self.called_at:
            return int((timezone.now() - self.checked_in_at).total_seconds() // 60)
        return 0

    def generate_number(self):
        day = self.checked_in_at.date() if self.checked_in_at else timezone.now().date()
        count = (
            Queue.all_objects.filter(department=self.department, checked_in_at__date=day)
            .exclude(id=self.id)
            .count()
            + 1
        )
        prefix = self.department.code[:3].upper() or "DEP"
        return f"Q-{prefix}-{day.strftime('%y%m%d')}-{count:03d}"
