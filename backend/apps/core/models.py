from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class BaseModel(models.Model):
    """Common fields for every business entity in the system."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.updated_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"])

    def restore(self, user=None):
        self.is_deleted = False
        self.deleted_at = None
        self.updated_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "updated_by", "updated_at"])


class AuditLog(models.Model):
    """Immutable log of sensitive actions performed in the system."""

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_VIEW = "view"
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_DISPENSE = "dispense"
    ACTION_PAYMENT = "payment"
    ACTION_PERMISSION_CHANGE = "permission_change"
    ACTION_UPLOAD = "upload"
    ACTION_DOWNLOAD = "download"
    ACTION_OTHER = "other"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
        (ACTION_VIEW, "View"),
        (ACTION_LOGIN, "Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_DISPENSE, "Dispense"),
        (ACTION_PAYMENT, "Payment"),
        (ACTION_PERMISSION_CHANGE, "Permission Change"),
        (ACTION_UPLOAD, "Upload"),
        (ACTION_DOWNLOAD, "Download"),
        (ACTION_OTHER, "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    module = models.CharField(max_length=64, db_index=True)
    record = models.CharField(max_length=255, blank=True, db_index=True)
    object_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["module", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.module} by {self.user}"


class Notification(models.Model):
    """In-app notification delivered to a user. Email/SMS hooks are async-safe."""

    TYPE_APPOINTMENT = "appointment"
    TYPE_LAB_RESULT = "lab_result"
    TYPE_PRESCRIPTION = "prescription"
    TYPE_LOW_STOCK = "low_stock"
    TYPE_PAYMENT = "payment"
    TYPE_ADMISSION = "admission"
    TYPE_DISCHARGE = "discharge"
    TYPE_BALANCE = "balance"
    TYPE_BED_ASSIGNMENT = "bed_assignment"
    TYPE_TRANSFER = "transfer"
    TYPE_HANDOVER = "handover"
    TYPE_ICU_ALERT = "icu_alert"
    TYPE_VITALS = "vitals"
    TYPE_SHIFT_REMINDER = "shift_reminder"
    TYPE_GENERAL = "general"

    TYPE_CHOICES = [
        (TYPE_APPOINTMENT, "Appointment"),
        (TYPE_LAB_RESULT, "Lab Result"),
        (TYPE_PRESCRIPTION, "Prescription"),
        (TYPE_LOW_STOCK, "Low Stock"),
        (TYPE_PAYMENT, "Payment"),
        (TYPE_ADMISSION, "Admission"),
        (TYPE_DISCHARGE, "Discharge"),
        (TYPE_BALANCE, "Balance"),
        (TYPE_BED_ASSIGNMENT, "Bed Assignment"),
        (TYPE_TRANSFER, "Patient Transfer"),
        (TYPE_HANDOVER, "Shift Handover"),
        (TYPE_ICU_ALERT, "ICU Alert"),
        (TYPE_VITALS, "Vital Signs"),
        (TYPE_SHIFT_REMINDER, "Shift Reminder"),
        (TYPE_GENERAL, "General"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_URGENT, "Urgent"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES, default=TYPE_GENERAL)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    related_module = models.CharField(max_length=64, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"


class Document(models.Model):
    """Uploaded patient/administrative documents with role-based access."""

    CATEGORY_MEDICAL_REPORT = "medical_report"
    CATEGORY_LAB_REPORT = "lab_report"
    CATEGORY_IMAGING_REPORT = "imaging_report"
    CATEGORY_INSURANCE = "insurance"
    CATEGORY_IDENTIFICATION = "identification"
    CATEGORY_DISCHARGE_SUMMARY = "discharge_summary"
    CATEGORY_REFERRAL = "referral"
    CATEGORY_OTHER = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_MEDICAL_REPORT, "Medical Report"),
        (CATEGORY_LAB_REPORT, "Lab Report"),
        (CATEGORY_IMAGING_REPORT, "Imaging Report"),
        (CATEGORY_INSURANCE, "Insurance Document"),
        (CATEGORY_IDENTIFICATION, "Identification"),
        (CATEGORY_DISCHARGE_SUMMARY, "Discharge Summary"),
        (CATEGORY_REFERRAL, "Referral Letter"),
        (CATEGORY_OTHER, "Other"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="documents/%Y/%m/")
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}"
