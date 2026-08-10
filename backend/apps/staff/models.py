from django.conf import settings
from django.db import models


class Staff(models.Model):
    """Employee record linked to a system user."""

    STATUS_ACTIVE = "active"
    STATUS_ON_LEAVE = "on_leave"
    STATUS_TERMINATED = "terminated"
    STATUS_INACTIVE = "inactive"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ON_LEAVE, "On Leave"),
        (STATUS_TERMINATED, "Terminated"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile"
    )
    employee_id = models.CharField(max_length=32, unique=True)
    job_title = models.CharField(max_length=120, blank=True)
    license_number = models.CharField(max_length=64, blank=True)
    qualifications = models.TextField(blank=True)
    date_joined = models.DateField()
    employment_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


class Shift(models.Model):
    name = models.CharField(max_length=64)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.start_time:%H:%M} - {self.end_time:%H:%M})"


class Attendance(models.Model):
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_LATE = "late"
    STATUS_LEAVE = "leave"

    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LATE, "Late"),
        (STATUS_LEAVE, "On Leave"),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(db_index=True)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PRESENT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ["staff", "date"]

    def __str__(self):
        return f"{self.staff} @ {self.date}"


class LeaveRequest(models.Model):
    TYPE_ANNUAL = "annual"
    TYPE_SICK = "sick"
    TYPE_UNPAID = "unpaid"
    TYPE_MATERNITY = "maternity"
    TYPE_PATERNITY = "paternity"
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_ANNUAL, "Annual"),
        (TYPE_SICK, "Sick"),
        (TYPE_UNPAID, "Unpaid"),
        (TYPE_MATERNITY, "Maternity"),
        (TYPE_PATERNITY, "Paternity"),
        (TYPE_OTHER, "Other"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_ANNUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.staff} {self.leave_type} {self.start_date} -> {self.end_date}"
