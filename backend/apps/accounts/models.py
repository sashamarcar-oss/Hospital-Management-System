from django.contrib.auth.models import AbstractUser
from django.db import models


class Permission(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    module = models.CharField(max_length=64, db_index=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self):
        return f"{self.module}.{self.code}"


class Role(models.Model):
    """System role. Each user belongs to exactly one role."""

    CODE_SUPER_ADMIN = "super_admin"
    CODE_ADMIN = "admin"
    CODE_RECEPTIONIST = "receptionist"
    CODE_DOCTOR = "doctor"
    CODE_NURSE = "nurse"
    CODE_ICU_NURSE = "icu_nurse"
    CODE_LAB_TECHNICIAN = "lab_technician"
    CODE_RADIOLOGIST = "radiologist"
    CODE_PHARMACIST = "pharmacist"
    CODE_ACCOUNTANT = "accountant"
    CODE_HR = "hr"
    CODE_PATIENT = "patient"

    ROLE_CHOICES = [
        (CODE_SUPER_ADMIN, "Super Admin"),
        (CODE_ADMIN, "Hospital Administrator"),
        (CODE_RECEPTIONIST, "Receptionist"),
        (CODE_DOCTOR, "Doctor"),
        (CODE_NURSE, "Nurse"),
        (CODE_ICU_NURSE, "ICU Nurse"),
        (CODE_LAB_TECHNICIAN, "Laboratory Technician"),
        (CODE_RADIOLOGIST, "Radiologist / Radiology Technician"),
        (CODE_PHARMACIST, "Pharmacist"),
        (CODE_ACCOUNTANT, "Accountant / Cashier"),
        (CODE_HR, "HR / Staff Manager"),
        (CODE_PATIENT, "Patient"),
    ]

    code = models.CharField(max_length=32, choices=ROLE_CHOICES, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")
    is_system = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    @property
    def dashboard_path(self):
        return {
            self.CODE_SUPER_ADMIN: "/dashboard",
            self.CODE_ADMIN: "/dashboard",
            self.CODE_RECEPTIONIST: "/queue",
            self.CODE_DOCTOR: "/consultations",
            self.CODE_NURSE: "/inpatient/bed-board",
            self.CODE_ICU_NURSE: "/icu/monitoring",
            self.CODE_LAB_TECHNICIAN: "/laboratory",
            self.CODE_PHARMACIST: "/pharmacy",
            self.CODE_ACCOUNTANT: "/billing",
            self.CODE_HR: "/staff",
            self.CODE_PATIENT: "/portal",
        }.get(self.code, "/dashboard")


class User(AbstractUser):
    role = models.ForeignKey(
        Role, null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    phone = models.CharField(max_length=32, blank=True)
    profile_photo = models.ImageField(upload_to="profiles/%Y/%m/", null=True, blank=True)
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    is_patient_account = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_joined"]

    @property
    def role_code(self):
        return self.role.code if self.role else None

    @property
    def role_name(self):
        return self.role.name if self.role else "No Role"

    @property
    def dashboard_path(self):
        return self.role.dashboard_path if self.role else "/login"

    def has_permission_code(self, code):
        """Check whether the user's role grants a permission code."""
        if not self.role:
            return False
        if self.role.code == Role.CODE_SUPER_ADMIN:
            return True
        return self.role.permissions.filter(code=code).exists()

    def has_any_permission_code(self, codes):
        return any(self.has_permission_code(code) for code in codes)

    def in_roles(self, *codes):
        return self.role_code in codes

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role_name})"
