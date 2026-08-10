from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class LabTestCatalog(BaseModel):
    """Configurable catalog of laboratory tests."""

    CATEGORY_CHOICES = [
        ("hematology", "Hematology"),
        ("biochemistry", "Biochemistry"),
        ("microbiology", "Microbiology"),
        ("urinalysis", "Urinalysis"),
        ("serology", "Serology"),
        ("immunology", "Immunology"),
        ("pathology", "Pathology"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="other")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sample_type = models.CharField(max_length=64, blank=True, help_text="e.g. blood, urine, swab")
    normal_range = models.CharField(max_length=120, blank=True)
    units = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LabRequest(BaseModel):
    STATUS_REQUESTED = "requested"
    STATUS_SAMPLE_COLLECTED = "sample_collected"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_REVIEWED = "reviewed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_REQUESTED, "Requested"),
        (STATUS_SAMPLE_COLLECTED, "Sample Collected"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PRIORITY_ROUTINE = "routine"
    PRIORITY_URGENT = "urgent"
    PRIORITY_STAT = "stat"

    PRIORITY_CHOICES = [
        (PRIORITY_ROUTINE, "Routine"),
        (PRIORITY_URGENT, "Urgent"),
        (PRIORITY_STAT, "STAT"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="lab_requests")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_requests")
    consultation = models.ForeignKey(
        "clinical.Consultation", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lab_requests",
    )
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_ROUTINE)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    clinical_notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["status", "requested_at"])]

    def __str__(self):
        return f"Lab request {self.id} - {self.patient}"

    @property
    def test_count(self):
        return self.items.count()

    @property
    def total_price(self):
        return sum(item.test.price for item in self.items.all())


class LabRequestItem(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_SAMPLE_COLLECTED = "sample_collected"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SAMPLE_COLLECTED, "Sample Collected"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
    ]

    lab_request = models.ForeignKey(LabRequest, on_delete=models.CASCADE, related_name="items")
    test = models.ForeignKey(LabTestCatalog, on_delete=models.CASCADE, related_name="request_items")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __str__(self):
        return f"{self.test.name} ({self.status})"


class LabResult(BaseModel):
    """Result entry for a specific test within a request."""

    request_item = models.OneToOneField(
        LabRequestItem, on_delete=models.CASCADE, related_name="result"
    )
    result = models.TextField(blank=True)
    units = models.CharField(max_length=32, blank=True)
    reference_range = models.CharField(max_length=120, blank=True)
    comments = models.TextField(blank=True)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    report_file = models.FileField(upload_to="lab_reports/%Y/%m/", null=True, blank=True)
    is_abnormal = models.BooleanField(default=False)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"Result for {self.request_item.test.name}"
