from django.conf import settings
from django.db import models
from django.db.models import Q
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
    STATUS_CLEANING = "cleaning"
    STATUS_OUT_OF_SERVICE = "out_of_service"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_CLEANING, "Cleaning"),
        (STATUS_OUT_OF_SERVICE, "Out of Service"),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_number = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    notes = models.TextField(blank=True, help_text="Bed-specific notes (equipment, accessibility, etc.).")
    last_cleaned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["bed_number"]
        unique_together = ["room", "bed_number"]

    def __str__(self):
        return f"{self.room} - Bed {self.bed_number} ({self.status})"

    @property
    def current_patient(self):
        active = self.assignment_history.filter(released_at__isnull=True).select_related("admission__patient").first()
        return active.admission.patient if active and active.admission else None

    @property
    def current_admission(self):
        active = self.assignment_history.filter(released_at__isnull=True).select_related("admission").first()
        return active.admission if active else None


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
    admission_number = models.CharField(max_length=32, unique=True, editable=False, blank=True)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="admissions"
    )
    assigned_nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_nursing_assignments",
        help_text="Primary nurse responsible for this admission.",
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
    expected_discharge_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ADMITTED)
    discharged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-admission_date"]
        indexes = [models.Index(fields=["status", "admission_date"])]

    def __str__(self):
        return f"{self.patient} admitted {self.admission_date:%Y-%m-%d}"

    def save(self, *args, **kwargs):
        if not self.admission_number:
            self.admission_number = self._generate_number()
        super().save(*args, **kwargs)
        self._sync_bed()

    def _generate_number(self):
        year = timezone.now().year
        prefix = f"ADM-{year}-"
        last = (
            Admission.all_objects.filter(admission_number__startswith=prefix)
            .order_by("-id")
            .values_list("admission_number", flat=True)
            .first()
        )
        base = int(last.split("-")[-1]) + 1 if last else 1
        number = f"{prefix}{base:05d}"
        while Admission.all_objects.filter(admission_number=number).exists():
            base += 1
            number = f"{prefix}{base:05d}"
        return number

    def _sync_bed(self):
        """Denormalized convenience: mark the linked bed occupied when admitted.

        Bed status lifecycle is authoritative in the bed-management services;
        this only guarantees a bed set directly on an admitted admission is
        never left visibly free.
        """
        if self.bed_id and self.status == self.STATUS_ADMITTED:
            Bed.objects.filter(pk=self.bed_id).update(status=Bed.STATUS_OCCUPIED)

    @property
    def active_bed_assignment(self):
        return self.bed_assignments.filter(released_at__isnull=True).select_related("bed").first()


class BedAssignment(BaseModel):
    """Immutable, append-only history of an admission's use of a bed.

    One active assignment may exist per admission and per bed at any time.
    Transfers close the old assignment and open a new one atomically.
    """

    STATUS_ACTIVE = "active"
    STATUS_RELEASED = "released"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_RELEASED, "Released"),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="bed_assignments")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="assignment_history")
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    assigned_at = models.DateTimeField(default=timezone.now)
    expected_discharge_date = models.DateField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="bed_assignments_made"
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="bed_assignments_released"
    )
    release_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["admission", "-assigned_at"]),
            models.Index(fields=["bed", "-assigned_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["admission"],
                condition=Q(released_at__isnull=True),
                name="uniq_active_admission_bed_assignment",
            ),
            models.UniqueConstraint(
                fields=["bed"],
                condition=Q(released_at__isnull=True),
                name="uniq_active_bed_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.admission} -> {self.bed}"

    @property
    def is_active(self):
        return self.released_at is None

    @property
    def status(self):
        return self.STATUS_ACTIVE if self.is_active else self.STATUS_RELEASED

    def release(self, user=None, reason="", released_at=None):
        self.released_at = released_at or timezone.now()
        self.released_by = user
        self.release_reason = reason
        self.save(update_fields=["released_at", "released_by", "release_reason", "updated_at"])


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


class NurseAssignment(BaseModel):
    """Assignment of a nurse to an admission (history preserved)."""

    ROLE_PRIMARY = "primary"
    ROLE_RELIEF = "relief"
    ROLE_ASSIST = "assist"

    ROLE_CHOICES = [
        (ROLE_PRIMARY, "Primary Nurse"),
        (ROLE_RELIEF, "Relief Nurse"),
        (ROLE_ASSIST, "Assisting Nurse"),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="nurse_assignments")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inpatient_nurse_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_PRIMARY)
    assigned_at = models.DateTimeField(default=timezone.now)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["admission", "nurse"],
                condition=Q(unassigned_at__isnull=True),
                name="uniq_active_nurse_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.nurse} -> {self.admission}"


class NursingNote(BaseModel):
    """Digital nursing shift note with draft / submitted / amended lifecycle.

    Submitted notes are immutable. Corrections create an amendment linked to
    this record; the original is never silently overwritten.
    """

    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_AMENDED = "amended"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_AMENDED, "Amended"),
    ]

    SHIFT_MORNING = "morning"
    SHIFT_AFTERNOON = "afternoon"
    SHIFT_NIGHT = "night"

    SHIFT_CHOICES = [
        (SHIFT_MORNING, "Morning"),
        (SHIFT_AFTERNOON, "Afternoon / Evening"),
        (SHIFT_NIGHT, "Night"),
    ]

    CONDITION_CHOICES = [
        ("stable", "Stable"),
        ("improving", "Improving"),
        ("deteriorating", "Deteriorating"),
        ("critical", "Critical"),
    ]

    CONSCIOUSNESS_CHOICES = [
        ("alert", "Alert"),
        ("confused", "Confused"),
        ("drowsy", "Drowsy"),
        ("responsive_to_voice", "Responsive to voice"),
        ("responsive_to_pain", "Responsive to pain"),
        ("unresponsive", "Unresponsive"),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="nursing_notes")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    shift_type = models.CharField(max_length=16, choices=SHIFT_CHOICES, blank=True, default="")
    shift = models.CharField(max_length=32, blank=True, help_text="Free-text shift label for legacy notes.")
    note_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    amended_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="amendments"
    )
    amendment_reason = models.TextField(blank=True)

    condition = models.CharField(max_length=16, choices=CONDITION_CHOICES, default="stable")
    consciousness = models.CharField(max_length=32, choices=CONSCIOUSNESS_CHOICES, blank=True, default="")
    pain_assessment = models.CharField(max_length=120, blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    mobility = models.CharField(max_length=120, blank=True)
    nutrition_intake = models.CharField(max_length=120, blank=True)
    fluid_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    fluid_output_ml = models.PositiveIntegerField(null=True, blank=True)
    medication_observations = models.TextField(blank=True)
    wound_dressing_observations = models.TextField(blank=True)
    patient_complaints = models.TextField(blank=True)
    interventions = models.TextField(blank=True)
    patient_response = models.TextField(blank=True)
    safety_concerns = models.TextField(blank=True)
    fall_risk = models.CharField(max_length=32, blank=True, default="")
    doctor_instructions = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    pending_tasks = models.TextField(blank=True)

    handover_current_condition = models.TextField(blank=True)
    handover_recent_changes = models.TextField(blank=True)
    handover_interventions_provided = models.TextField(blank=True)
    handover_pending_tasks = models.TextField(blank=True)
    handover_important_observations = models.TextField(blank=True)
    handover_follow_up_required = models.TextField(blank=True)

    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["admission", "-recorded_at"])]

    def __str__(self):
        return f"Nursing note {self.recorded_at:%Y-%m-%d %H:%M} ({self.status})"

    def submit(self, user=None):
        if self.status != self.STATUS_SUBMITTED:
            self.status = self.STATUS_SUBMITTED
            self.submitted_at = timezone.now()
            self.updated_by = user
            self.save(update_fields=["status", "submitted_at", "updated_by", "updated_at"])
        elif self.submitted_at is None:
            self.submitted_at = timezone.now()
            self.updated_by = user
            self.save(update_fields=["submitted_at", "updated_by", "updated_at"])

    def amend(self, user, reason, changed_fields, snapshot):
        """Create an amendment of this note. The original record is preserved."""
        amended = NursingNote.objects.get(pk=self.pk)
        amended.pk = None
        amended.id = None
        amended.created_at = None
        amended.updated_at = None
        amended.recorded_at = timezone.now()
        amended.status = self.STATUS_AMENDED
        amended.amended_from = self
        amended.amendment_reason = reason
        amended.updated_by = user
        for field, value in changed_fields.items():
            if hasattr(amended, field):
                setattr(amended, field, value)
        amended.save()
        NursingNoteAmendment.objects.create(
            note=amended,
            amended_by=user,
            reason=reason,
            changed_fields=changed_fields,
            previous_snapshot=snapshot,
        )
        return amended


class NursingNoteAmendment(BaseModel):
    """Audit record for a nursing note amendment."""

    note = models.ForeignKey(NursingNote, on_delete=models.CASCADE, related_name="note_amendments")
    amended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    amended_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    changed_fields = models.JSONField(default=dict)
    previous_snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ["-amended_at"]

    def __str__(self):
        return f"Amendment {self.amended_at:%Y-%m-%d %H:%M}"


class NursingHandover(BaseModel):
    """Structured shift handover produced at the end of a nursing shift."""

    SHIFT_CHOICES = NursingNote.SHIFT_CHOICES
    CONDITION_CHOICES = NursingNote.CONDITION_CHOICES

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="handovers")
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="handovers_made"
    )
    incoming_nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="handovers_received"
    )
    shift = models.CharField(max_length=32, blank=True)
    shift_type = models.CharField(max_length=16, choices=SHIFT_CHOICES, blank=True, default="")
    handover_date = models.DateField(default=timezone.localdate)
    condition = models.CharField(max_length=16, choices=CONDITION_CHOICES, default="stable")
    current_condition = models.TextField(blank=True)
    recent_changes = models.TextField(blank=True)
    interventions_provided = models.TextField(blank=True)
    pending_tasks = models.TextField(blank=True)
    important_observations = models.TextField(blank=True)
    follow_up_required = models.TextField(blank=True)
    medication_due = models.TextField(blank=True)
    pending_investigations = models.TextField(blank=True)
    precautions = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["admission", "-recorded_at"])]

    def __str__(self):
        return f"Handover {self.recorded_at:%Y-%m-%d %H:%M}"


class ICUMonitoringSheet(BaseModel):
    """A configured ICU monitoring sheet for a patient's critical-care stay."""

    PERIOD_MORNING = "morning"
    PERIOD_AFTERNOON = "afternoon"
    PERIOD_NIGHT = "night"

    PERIOD_CHOICES = [
        (PERIOD_MORNING, "Morning"),
        (PERIOD_AFTERNOON, "Afternoon / Evening"),
        (PERIOD_NIGHT, "Night"),
    ]

    INTERVAL_15 = "15_minutes"
    INTERVAL_30 = "30_minutes"
    INTERVAL_HOURLY = "hourly"
    INTERVAL_2_HOURLY = "2_hourly"
    INTERVAL_4_HOURLY = "4_hourly"

    INTERVAL_CHOICES = [
        (INTERVAL_15, "Every 15 minutes"),
        (INTERVAL_30, "Every 30 minutes"),
        (INTERVAL_HOURLY, "Hourly"),
        (INTERVAL_2_HOURLY, "2-hourly"),
        (INTERVAL_4_HOURLY, "4-hourly"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="icu_sheets")
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name="icu_sheets")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="icu_sheets_nurse"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="icu_sheets_doctor"
    )
    monitoring_date = models.DateField(default=timezone.localdate)
    period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default=PERIOD_MORNING)
    interval = models.CharField(max_length=16, choices=INTERVAL_CHOICES, default=INTERVAL_HOURLY)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-monitoring_date", "period"]
        indexes = [models.Index(fields=["admission", "-monitoring_date"])]

    def __str__(self):
        return f"ICU sheet {self.monitoring_date} ({self.period})"


class ICUMonitoringRecord(BaseModel):
    """A single time-based ICU observation row attached to a monitoring sheet."""

    CONSCIOUSNESS_CHOICES = NursingNote.CONSCIOUSNESS_CHOICES
    PUPIL_CHOICES = [
        ("reactive", "Reactive"),
        ("sluggish", "Sluggish"),
        ("fixed", "Fixed"),
        ("dilated", "Dilated"),
        ("equal_reactive", "Equal & reactive"),
    ]
    OXYGEN_THERAPY_CHOICES = [
        ("room_air", "Room air"),
        ("nasal_cannula", "Nasal cannula"),
        ("face_mask", "Face mask"),
        ("rebreather_mask", "Non-rebreather mask"),
        ("venturi", "Venturi mask"),
        ("mechanical_ventilation", "Mechanical ventilation"),
    ]
    RESPIRATORY_SUPPORT_CHOICES = [
        ("spontaneous", "Spontaneous"),
        ("oxygen_therapy", "Oxygen therapy"),
        ("bipap", "BiPAP"),
        ("cpap", "CPAP"),
        ("mechanical_ventilation", "Mechanical ventilation"),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="icu_records")
    sheet = models.ForeignKey(
        ICUMonitoringSheet, null=True, blank=True, on_delete=models.CASCADE, related_name="records"
    )
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    recorded_at = models.DateTimeField(default=timezone.now)
    frequency = models.CharField(
        max_length=16,
        choices=ICUMonitoringSheet.INTERVAL_CHOICES,
        default=ICUMonitoringSheet.INTERVAL_HOURLY,
    )

    # VITALS
    temperature = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=24, blank=True, help_text="e.g. 120/80")
    blood_pressure_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    map_arterial = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Mean arterial pressure (mmHg)")
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    oxygen_saturation = models.PositiveSmallIntegerField(null=True, blank=True)
    spo2 = models.PositiveSmallIntegerField(null=True, blank=True)

    # RESPIRATORY
    oxygen_therapy = models.CharField(max_length=32, choices=OXYGEN_THERAPY_CHOICES, blank=True, default="")
    oxygen_flow_rate = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="L/min")
    respiratory_support = models.CharField(max_length=32, choices=RESPIRATORY_SUPPORT_CHOICES, blank=True, default="")
    ventilator_mode = models.CharField(max_length=64, blank=True)
    ventilator_settings = models.TextField(blank=True)

    # NEUROLOGICAL
    consciousness = models.CharField(max_length=32, choices=CONSCIOUSNESS_CHOICES, blank=True, default="")
    gcs_eye = models.PositiveSmallIntegerField(null=True, blank=True)
    gcs_verbal = models.PositiveSmallIntegerField(null=True, blank=True)
    gcs_motor = models.PositiveSmallIntegerField(null=True, blank=True)
    pupil_left = models.CharField(max_length=32, choices=PUPIL_CHOICES, blank=True, default="")
    pupil_right = models.CharField(max_length=32, choices=PUPIL_CHOICES, blank=True, default="")

    # FLUID BALANCE
    oral_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    iv_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    fluid_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    urine_output_ml = models.PositiveIntegerField(null=True, blank=True)
    drain_output_ml = models.PositiveIntegerField(null=True, blank=True)
    other_output_ml = models.PositiveIntegerField(null=True, blank=True)
    fluid_output_ml = models.PositiveIntegerField(null=True, blank=True)

    # OTHER OBSERVATIONS
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_glucose = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="mmol/L")
    skin_condition = models.CharField(max_length=120, blank=True)
    pressure_injury_risk = models.CharField(max_length=120, blank=True)
    positioning = models.CharField(max_length=120, blank=True)
    infusions = models.TextField(blank=True)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["recorded_at"]
        indexes = [models.Index(fields=["admission", "recorded_at"])]

    def __str__(self):
        return f"ICU record {self.recorded_at:%Y-%m-%d %H:%M}"

    @property
    def gcs_total(self):
        if None in (self.gcs_eye, self.gcs_verbal, self.gcs_motor):
            return None
        return self.gcs_eye + self.gcs_verbal + self.gcs_motor

    @property
    def total_intake_ml(self):
        if self.fluid_intake_ml is not None:
            return self.fluid_intake_ml
        return (self.oral_intake_ml or 0) + (self.iv_intake_ml or 0) or None

    @property
    def total_output_ml(self):
        if self.fluid_output_ml is not None:
            return self.fluid_output_ml
        return (self.urine_output_ml or 0) + (self.drain_output_ml or 0) + (self.other_output_ml or 0) or None

    @property
    def net_balance_ml(self):
        intake = self.total_intake_ml
        output = self.total_output_ml
        if intake is None and output is None:
            return None
        return (intake or 0) - (output or 0)

    @property
    def effective_spo2(self):
        return self.spo2 if self.spo2 is not None else self.oxygen_saturation

    def save(self, *args, **kwargs):
        if self.spo2 is None and self.oxygen_saturation is not None:
            self.spo2 = self.oxygen_saturation
        if self.oxygen_saturation is None and self.spo2 is not None:
            self.oxygen_saturation = self.spo2
        if self.blood_pressure and not (self.blood_pressure_systolic or self.blood_pressure_diastolic):
            parts = self.blood_pressure.replace(" ", "").split("/")
            if len(parts) == 2:
                try:
                    self.blood_pressure_systolic = int(parts[0])
                    self.blood_pressure_diastolic = int(parts[1])
                except ValueError:
                    pass
        super().save(*args, **kwargs)


class FluidBalance(BaseModel):
    """Shift-level fluid balance chart for an inpatient admission."""

    PERIOD_CHOICES = ICUMonitoringSheet.PERIOD_CHOICES

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name="fluid_balances")
    nurse = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    balance_date = models.DateField(default=timezone.localdate)
    period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default="morning")
    oral_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    iv_intake_ml = models.PositiveIntegerField(null=True, blank=True)
    urine_output_ml = models.PositiveIntegerField(null=True, blank=True)
    drain_output_ml = models.PositiveIntegerField(null=True, blank=True)
    other_output_ml = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-balance_date", "period"]
        indexes = [models.Index(fields=["admission", "-balance_date"])]

    def __str__(self):
        return f"Fluid balance {self.balance_date} ({self.period})"

    @property
    def total_intake_ml(self):
        return (self.oral_intake_ml or 0) + (self.iv_intake_ml or 0) or None

    @property
    def total_output_ml(self):
        return (self.urine_output_ml or 0) + (self.drain_output_ml or 0) + (self.other_output_ml or 0) or None

    @property
    def net_balance_ml(self):
        intake = self.total_intake_ml
        output = self.total_output_ml
        if intake is None and output is None:
            return None
        return (intake or 0) - (output or 0)


class ICUThreshold(BaseModel):
    """Configurable clinical alert thresholds for ICU parameters.

    Thresholds are clinical decision support only: they flag values for
    review and never constitute a diagnosis. Authorized clinical
    administrators manage these records.
    """

    PARAM_HR = "heart_rate"
    PARAM_TEMP = "temperature"
    PARAM_BP_SYS = "bp_systolic"
    PARAM_BP_DIA = "bp_diastolic"
    PARAM_MAP = "map"
    PARAM_RR = "respiratory_rate"
    PARAM_SPO2 = "spo2"
    PARAM_GLUCOSE = "blood_glucose"
    PARAM_GCS = "gcs_total"
    PARAM_PAIN = "pain_score"

    PARAM_CHOICES = [
        (PARAM_HR, "Heart rate (bpm)"),
        (PARAM_TEMP, "Temperature (°C)"),
        (PARAM_BP_SYS, "Systolic BP (mmHg)"),
        (PARAM_BP_DIA, "Diastolic BP (mmHg)"),
        (PARAM_MAP, "Mean arterial pressure (mmHg)"),
        (PARAM_RR, "Respiratory rate (bpm)"),
        (PARAM_SPO2, "SpO2 (%)"),
        (PARAM_GLUCOSE, "Blood glucose (mmol/L)"),
        (PARAM_GCS, "GCS total"),
        (PARAM_PAIN, "Pain score"),
    ]

    SEVERITY_ALERT = "alert"
    SEVERITY_CRITICAL = "critical"

    SEVERITY_CHOICES = [
        (SEVERITY_ALERT, "Alert"),
        (SEVERITY_CRITICAL, "Critical"),
    ]

    parameter = models.CharField(max_length=32, choices=PARAM_CHOICES, unique=True)
    name = models.CharField(max_length=64, blank=True)
    unit = models.CharField(max_length=24, blank=True)
    min_alert = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    max_alert = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    min_critical = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    max_critical = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name or self.get_parameter_display()

    def evaluate(self, value):
        """Return a list of alerts for a numeric value, ordered by severity."""
        if value is None or not self.is_active:
            return []
        value = float(value)
        alerts = []
        if self.min_critical is not None and value < float(self.min_critical):
            alerts.append({"severity": self.SEVERITY_CRITICAL, "parameter": self.parameter, "direction": "low"})
        elif self.min_alert is not None and value < float(self.min_alert):
            alerts.append({"severity": self.SEVERITY_ALERT, "parameter": self.parameter, "direction": "low"})
        if self.max_critical is not None and value > float(self.max_critical):
            alerts.append({"severity": self.SEVERITY_CRITICAL, "parameter": self.parameter, "direction": "high"})
        elif self.max_alert is not None and value > float(self.max_alert):
            alerts.append({"severity": self.SEVERITY_ALERT, "parameter": self.parameter, "direction": "high"})
        return alerts
