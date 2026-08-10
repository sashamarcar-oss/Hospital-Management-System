from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class RadiologyRequest(BaseModel):
    STATUS_REQUESTED = "requested"
    STATUS_QUEUED = "queued"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_REVIEWED = "reviewed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Requested"),
        (STATUS_QUEUED, "Queued"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PROCEDURE_XRAY = "xray"
    PROCEDURE_ULTRASOUND = "ultrasound"
    PROCEDURE_CT = "ct_scan"
    PROCEDURE_MRI = "mri"
    PROCEDURE_OTHER = "other"

    PROCEDURE_CHOICES = [
        (PROCEDURE_XRAY, "X-Ray"),
        (PROCEDURE_ULTRASOUND, "Ultrasound"),
        (PROCEDURE_CT, "CT Scan"),
        (PROCEDURE_MRI, "MRI"),
        (PROCEDURE_OTHER, "Other Imaging"),
    ]

    PRIORITY_ROUTINE = "routine"
    PRIORITY_URGENT = "urgent"
    PRIORITY_STAT = "stat"

    PRIORITY_CHOICES = [
        (PRIORITY_ROUTINE, "Routine"),
        (PRIORITY_URGENT, "Urgent"),
        (PRIORITY_STAT, "STAT"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="radiology_requests")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="radiology_requests")
    consultation = models.ForeignKey(
        "clinical.Consultation", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="radiology_requests",
    )
    procedure_type = models.CharField(max_length=16, choices=PROCEDURE_CHOICES, default=PROCEDURE_XRAY)
    body_part = models.CharField(max_length=120, blank=True)
    clinical_indication = models.TextField(blank=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_ROUTINE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.get_procedure_type_display()} - {self.patient}"


class RadiologyReport(BaseModel):
    request = models.OneToOneField(
        RadiologyRequest, on_delete=models.CASCADE, related_name="report"
    )
    findings = models.TextField(blank=True)
    impression = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)
    radiologist = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    report_file = models.FileField(upload_to="radiology_reports/%Y/%m/", null=True, blank=True)
    completed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Report for {self.request}"
