from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Ward(BaseModel):
    TYPE_GENERAL = "general"
    TYPE_PRIVATE = "private"
    TYPE_ICU = "icu"
    TYPE_MATERNITY = "maternity"
    TYPE_PEDIATRICS = "pediatrics"
    TYPE_SURGICAL = "surgical"
    TYPE_EMERGENCY = "emergency"
    TYPE_ISOLATION = "isolation"

    TYPE_CHOICES = [
        (TYPE_GENERAL, "General"),
        (TYPE_PRIVATE, "Private"),
        (TYPE_ICU, "ICU"),
        (TYPE_MATERNITY, "Maternity"),
        (TYPE_PEDIATRICS, "Pediatrics"),
        (TYPE_SURGICAL, "Surgical"),
        (TYPE_EMERGENCY, "Emergency"),
        (TYPE_ISOLATION, "Isolation"),
    ]

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=16, blank=True)
    ward_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_GENERAL)
    department = models.ForeignKey(
        "departments.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="wards"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper()
        super().save(*args, **kwargs)

    @property
    def bed_count(self):
        return self.rooms.aggregate(total=models.Count("beds"))["total"] or 0

    @property
    def available_beds(self):
        return Bed.objects.filter(room__ward=self, status=Bed.STATUS_AVAILABLE).count()


class Room(BaseModel):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=32)
    room_type = models.CharField(max_length=64, default="general")

    class Meta:
        ordering = ["room_number"]
        unique_together = ["ward", "room_number"]

    def __str__(self):
        return f"{self.ward.name} - Room {self.room_number}"


class Bed(BaseModel):
    STATUS_AVAILABLE = "available"
    STATUS_OCCUPIED = "occupied"
    STATUS_RESERVED = "reserved"
    STATUS_MAINTENANCE = "maintenance"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_MAINTENANCE, "Maintenance"),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_number = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)

    class Meta:
        ordering = ["bed_number"]
        unique_together = ["room", "bed_number"]

    def __str__(self):
        return f"{self.room} - Bed {self.bed_number} ({self.status})"

    @property
    def current_patient(self):
        admission = self.admissions.filter(
            status__in=[Admission.STATUS_ADMITTED, Admission.STATUS_TRANSFERRED]
        ).first()
        return admission.patient if admission else None


class Admission(BaseModel):
    STATUS_ADMITTED = "admitted"
    STATUS_TRANSFERRED = "transferred"
    STATUS_DISCHARGED = "discharged"

    STATUS_CHOICES = [
        (STATUS_ADMITTED, "Admitted"),
        (STATUS_TRANSFERRED, "Transferred"),
        (STATUS_DISCHARGED, "Discharged"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="admissions")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions"
    )
    department = models.ForeignKey(
        "departments.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions"
    )
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions")
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions")
    admission_date = models.DateTimeField(default=timezone.now)
    admission_reason = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ADMITTED)
    discharged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-admission_date"]
        indexes = [models.Index(fields=["status", "admission_date"])]

    def __str__(self):
        return f"{self.patient} admitted {self.admission_date:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_bed()

    def _sync_bed(self):
        if self.bed:
            if self.status == self.STATUS_ADMITTED:
                Bed.objects.filter(pk=self.bed_id).update(status=Bed.STATUS_OCCUPIED)
            else:
                Bed.objects.filter(pk=self.bed_id).update(status=Bed.STATUS_AVAILABLE)


class Discharge(BaseModel):
    admission = models.OneToOneField(
        Admission, on_delete=models.CASCADE, related_name="discharge"
    )
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="discharges")
    discharge_date = models.DateTimeField(default=timezone.now)
    discharge_type = models.CharField(max_length=64, default="home", help_text="home, referral, against-medical-advice")
    diagnosis_summary = models.TextField(blank=True)
    treatment_summary = models.TextField(blank=True)
    medication = models.TextField(blank=True)
    outstanding_bills = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    doctor_notes = models.TextField(blank=True)
    discharged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-discharge_date"]

    def __str__(self):
        return f"Discharge {self.patient} on {self.discharge_date:%Y-%m-%d}"


class NursingNote(BaseModel):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="nursing_notes")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.TextField()
    shift = models.CharField(max_length=32, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"Nursing note {self.recorded_at:%Y-%m-%d %H:%M}"
