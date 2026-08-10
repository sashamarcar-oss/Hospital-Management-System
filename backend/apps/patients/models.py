import re

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Patient(BaseModel):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    BLOOD_GROUPS = [
        ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-"),
        ("unknown", "Unknown"),
    ]

    MARITAL_STATUS = [
        ("single", "Single"),
        ("married", "Married"),
        ("divorced", "Divorced"),
        ("widowed", "Widowed"),
    ]

    patient_number = models.CharField(max_length=32, unique=True, editable=False, db_index=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient_account",
        help_text="Optional linked patient portal account.",
    )
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    national_id = models.CharField(max_length=32, blank=True, db_index=True)
    phone = models.CharField(max_length=32, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    marital_status = models.CharField(max_length=16, choices=MARITAL_STATUS, default="single", blank=True)
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUPS, default="unknown")
    allergies = models.TextField(blank=True, help_text="Comma-separated list of allergies.")
    insurance_provider = models.CharField(max_length=120, blank=True)
    insurance_number = models.CharField(max_length=64, blank=True, db_index=True)
    next_of_kin_name = models.CharField(max_length=120, blank=True)
    next_of_kin_phone = models.CharField(max_length=32, blank=True)
    next_of_kin_relationship = models.CharField(max_length=64, blank=True)
    profile_photo = models.ImageField(upload_to="patients/%Y/%m/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.patient_number})"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def age(self):
        from datetime import date

        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def save(self, *args, **kwargs):
        if not self.patient_number:
            self.patient_number = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        last = (
            Patient.all_objects.all()
            .exclude(patient_number="")
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
        )
        base = (last or 0) + 1
        number = f"HMS-{base:07d}"
        while Patient.all_objects.filter(patient_number=number).exists():
            base += 1
            number = f"HMS-{base:07d}"
        return number


class EmergencyContact(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="emergency_contacts")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    relationship = models.CharField(max_length=64)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.relationship}) of {self.patient}"
