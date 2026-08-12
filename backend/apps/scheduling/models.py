from django.conf import settings
from django.db import models

class NurseShift(models.Model):
    TYPE_MORNING, TYPE_AFTERNOON, TYPE_NIGHT, TYPE_CUSTOM = "morning", "afternoon", "night", "custom"
    STATUS_SCHEDULED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_MISSED = "scheduled", "active", "completed", "cancelled", "missed"
    SHIFT_TYPES = [(TYPE_MORNING, "Morning"), (TYPE_AFTERNOON, "Afternoon"), (TYPE_NIGHT, "Night"), (TYPE_CUSTOM, "Custom")]
    STATUS_CHOICES = [(STATUS_SCHEDULED, "Scheduled"), (STATUS_ACTIVE, "Active"), (STATUS_COMPLETED, "Completed"), (STATUS_CANCELLED, "Cancelled"), (STATUS_MISSED, "Missed")]
    nurse = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="nurse_shifts")
    department = models.ForeignKey("departments.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="nurse_shifts")
    shift_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    shift_type = models.CharField(max_length=16, choices=SHIFT_TYPES, default=TYPE_CUSTOM)
    location = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_nurse_shifts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["shift_date", "start_time"]
        indexes = [models.Index(fields=["nurse", "shift_date"])]
