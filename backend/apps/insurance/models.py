from django.db import models

from apps.core.models import BaseModel


class InsuranceProvider(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=16, unique=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InsurancePolicy(BaseModel):
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    COVERAGE_OUTPATIENT = "outpatient"
    COVERAGE_INPATIENT = "inpatient"
    COVERAGE_BOTH = "both"

    COVERAGE_CHOICES = [
        (COVERAGE_OUTPATIENT, "Outpatient"),
        (COVERAGE_INPATIENT, "Inpatient"),
        (COVERAGE_BOTH, "Outpatient & Inpatient"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="insurance_policies")
    provider = models.ForeignKey(
        InsuranceProvider, on_delete=models.CASCADE, related_name="policies"
    )
    policy_number = models.CharField(max_length=64)
    membership_number = models.CharField(max_length=64, blank=True)
    coverage_type = models.CharField(max_length=16, choices=COVERAGE_CHOICES, default=COVERAGE_BOTH)
    coverage_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ["-start_date"]
        unique_together = ["provider", "policy_number"]

    def __str__(self):
        return f"{self.provider.name} - {self.policy_number}"


class InsuranceClaim(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_APPROVED = "approved"
    STATUS_PARTIALLY_APPROVED = "partially_approved"
    STATUS_REJECTED = "rejected"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_PARTIALLY_APPROVED, "Partially Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_PAID, "Paid"),
    ]

    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name="claims")
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="insurance_claims")
    invoice = models.ForeignKey(
        "billing.Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="insurance_claims"
    )
    claim_number = models.CharField(max_length=32, unique=True, editable=False)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    approved_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rejected_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    patient_contribution = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    submitted_date = models.DateField(null=True, blank=True)
    approval_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.claim_number

    def save(self, *args, **kwargs):
        if not self.claim_number:
            from django.utils import timezone

            year = timezone.now().year
            last = (
                InsuranceClaim.all_objects.filter(claim_number__startswith=f"CLM-{year}-")
                .order_by("-id").values_list("id", flat=True).first()
            )
            self.claim_number = f"CLM-{year}-{(last or 0) + 1:04d}"
        super().save(*args, **kwargs)
