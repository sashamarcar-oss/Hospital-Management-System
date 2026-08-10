from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class EmergencyVisit(BaseModel):
    PRIORITY_CRITICAL = "critical"
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"

    PRIORITY_CHOICES = [
        (PRIORITY_CRITICAL, "Critical"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_LOW, "Low"),
    ]

    STATUS_TRIAGE = "triage"
    STATUS_WAITING = "waiting"
    STATUS_IN_TREATMENT = "in_treatment"
    STATUS_ADMITTED = "admitted"
    STATUS_REFERRED = "referred"
    STATUS_DISCHARGED = "discharged"

    STATUS_CHOICES = [
        (STATUS_TRIAGE, "In Triage"),
        (STATUS_WAITING, "Waiting"),
        (STATUS_IN_TREATMENT, "In Treatment"),
        (STATUS_ADMITTED, "Admitted"),
        (STATUS_REFERRED, "Referred"),
        (STATUS_DISCHARGED, "Discharged"),
    ]

    MODE_CHOICES = [
        ("ambulance", "Ambulance"),
        ("walk_in", "Walk-in"),
        ("referred", "Referred"),
        ("police", "Police"),
        ("other", "Other"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="emergency_visits")
    arrival_time = models.DateTimeField(default=timezone.now)
    mode_of_arrival = models.CharField(max_length=16, choices=MODE_CHOICES, default="walk_in")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    chief_complaint = models.TextField(blank=True)
    triage_notes = models.TextField(blank=True)
    triage_score = models.PositiveSmallIntegerField(null=True, blank=True)
    vitals_summary = models.JSONField(null=True, blank=True, help_text="Snapshot of admission vitals.")
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="emergency_visits"
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_TRIAGE)
    treatment_notes = models.TextField(blank=True)
    referral_notes = models.TextField(blank=True)
    triaged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["priority", "arrival_time"]
        indexes = [models.Index(fields=["status", "priority"])]

    def __str__(self):
        return f"{self.get_priority_display()} - {self.patient}"

    @property
    def waiting_minutes(self):
        if self.arrival_time and self.status not in (
            self.STATUS_DISCHARGED, self.STATUS_ADMITTED, self.STATUS_REFERRED
        ):
            return int((timezone.now() - self.arrival_time).total_seconds() // 60)
        return 0
