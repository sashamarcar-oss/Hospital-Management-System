from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Consultation(BaseModel):
    """A single doctor-patient consultation / encounter."""

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="consultations")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consultations"
    )
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultations",
    )
    chief_complaint = models.TextField(blank=True)
    history_of_presenting_illness = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    physical_examination = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    procedures = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["patient", "-recorded_at"])]

    def __str__(self):
        return f"{self.patient} - {self.doctor} @ {self.recorded_at:%Y-%m-%d}"


class Diagnosis(BaseModel):
    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name="diagnoses"
    )
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="diagnoses")
    icd_code = models.CharField(max_length=16, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]

    def __str__(self):
        return f"{self.name} ({self.icd_code})"


class VitalSigns(BaseModel):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="vital_signs")
    admission = models.ForeignKey(
        "inpatient.Admission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vital_signs",
        help_text="Optional inpatient admission this reading belongs to.",
    )
    consultation = models.ForeignKey(
        Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="vital_signs"
    )
    temperature = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    pulse = models.PositiveSmallIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    oxygen_saturation = models.PositiveSmallIntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bmi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="mmol/L")
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient} vitals @ {self.recorded_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.weight is not None and self.height is not None and self.height > 0:
            height_m = float(self.height) / 100
            bmi = float(self.weight) / (height_m * height_m)
            self.bmi = round(bmi, 2)
        else:
            self.bmi = None
        super().save(*args, **kwargs)


class Prescription(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_PARTIALLY_DISPENSED = "partially_dispensed"
    STATUS_DISPENSED = "dispensed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PARTIALLY_DISPENSED, "Partially Dispensed"),
        (STATUS_DISPENSED, "Dispensed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="prescriptions")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prescriptions"
    )
    consultation = models.ForeignKey(
        Consultation, on_delete=models.SET_NULL, null=True, blank=True, related_name="prescriptions"
    )
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    dispensed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RX {self.id} - {self.patient}"

    def update_status(self):
        items = self.items.all()
        if not items:
            return
        total = sum(i.quantity for i in items)
        dispensed = sum(i.dispensed_quantity for i in items)
        if dispensed <= 0:
            self.status = self.STATUS_ACTIVE
        elif dispensed < total:
            self.status = self.STATUS_PARTIALLY_DISPENSED
        else:
            self.status = self.STATUS_DISPENSED
        self.save(update_fields=["status"])


class PrescriptionItem(BaseModel):
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name="items"
    )
    medicine = models.ForeignKey(
        "pharmacy.Medicine", on_delete=models.CASCADE, related_name="prescription_items"
    )
    dosage = models.CharField(max_length=64, blank=True)
    frequency = models.CharField(max_length=64, blank=True)
    duration = models.CharField(max_length=64, blank=True)
    route = models.CharField(max_length=32, default="oral")
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)
    dispensed_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.medicine} - {self.dosage} {self.frequency}"


class Referral(BaseModel):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_COMPLETED = "completed"
    STATUS_REJECTED = "rejected"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="referrals")
    from_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_made"
    )
    to_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals_received"
    )
    to_department = models.ForeignKey(
        "departments.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )
    consultation = models.ForeignKey(Consultation, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    diagnosis = models.ForeignKey(Diagnosis, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    specialty = models.CharField(max_length=120, blank=True)
    urgency = models.CharField(max_length=16, choices=[("routine", "Routine"), ("urgent", "Urgent"), ("emergency", "Emergency")], default="routine")
    referral_date = models.DateField(default=timezone.localdate)
    appointment_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    response_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Referral {self.patient}"
