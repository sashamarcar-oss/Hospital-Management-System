from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class ChargeType(BaseModel):
    """Configurable service charge types."""

    CATEGORY_CHOICES = [
        ("consultation", "Consultation"),
        ("laboratory", "Laboratory"),
        ("imaging", "Imaging"),
        ("medication", "Medication"),
        ("procedure", "Procedure"),
        ("admission", "Admission"),
        ("bed", "Bed Charge"),
        ("service", "Other Service"),
    ]

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, unique=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="service")
    default_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Invoice(BaseModel):
    STATUS_UNPAID = "unpaid"
    STATUS_PARTIALLY_PAID = "partially_paid"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"
    STATUS_INSURANCE_PENDING = "insurance_pending"
    STATUS_INSURANCE_APPROVED = "insurance_approved"
    STATUS_INSURANCE_REJECTED = "insurance_rejected"

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PARTIALLY_PAID, "Partially Paid"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_INSURANCE_PENDING, "Insurance Pending"),
        (STATUS_INSURANCE_APPROVED, "Insurance Approved"),
        (STATUS_INSURANCE_REJECTED, "Insurance Rejected"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=32, unique=True, editable=False)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_UNPAID)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    insurance_covered_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    patient_copay_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    insurance_claim = models.ForeignKey(
        "insurance.InsuranceClaim", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="invoices",
    )
    notes = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    issued_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [models.Index(fields=["status", "issued_at"])]

    def __str__(self):
        return self.invoice_number

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_number()
        self.recalculate(commit=False)
        super().save(*args, **kwargs)

    def _generate_number(self):
        year = timezone.now().year
        last = (
            Invoice.all_objects.filter(invoice_number__startswith=f"INV-{year}-")
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
        )
        return f"INV-{year}-{(last or 0) + 1:04d}"

    def recalculate(self, commit=True):
        if self.pk:
            items = list(self.items.all())
            subtotal = sum((i.line_total for i in items), Decimal("0"))
        else:
            items = []
            subtotal = Decimal("0")
        tax = subtotal * (Decimal(str(self.tax_rate)) / Decimal("100"))
        total = subtotal - Decimal(str(self.discount)) + tax
        if total < 0:
            total = Decimal("0")
        self.subtotal = round(subtotal, 2)
        self.tax = round(tax, 2)
        self.total = round(total, 2)
        self.amount_paid = round(self._paid_total(), 2)
        self.balance = round(self.total - self.amount_paid, 2)
        
        # Update status based on actual payments. An invoice becomes PAID only when
        # a real successful payment has cleared the outstanding balance.
        if self.status != self.STATUS_CANCELLED:
            if self.total > 0 and self.amount_paid > 0 and self.balance <= 0:
                self.status = self.STATUS_PAID
            elif self.amount_paid > 0 and self.balance > 0:
                self.status = self.STATUS_PARTIALLY_PAID
            elif self.amount_paid == 0 and self.balance > 0:
                if self.due_date and self.due_date < timezone.now().date():
                    self.status = self.STATUS_OVERDUE
                else:
                    self.status = self.STATUS_UNPAID
            else:
                self.status = self.STATUS_UNPAID
        
        if commit:
            self.save(update_fields=[
                "subtotal", "tax", "total", "amount_paid", "balance", "status",
            ])

    def _paid_total(self):
        if not self.pk:
            return 0
        return self.payments.filter(status=Payment.STATUS_COMPLETED).aggregate(
            total=models.Sum("amount")
        )["total"] or 0

    @classmethod
    def patient_credit(cls, patient, exclude_pk=None):
        """Total available credit (sum of negative balances) for a patient."""
        qs = cls.objects.filter(patient=patient)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        total_balance = qs.aggregate(total=models.Sum("balance"))["total"]
        if total_balance is None:
            return Decimal("0")
        return abs(total_balance) if total_balance < 0 else Decimal("0")


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    charge_type = models.ForeignKey(
        ChargeType, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_items"
    )
    consultation = models.ForeignKey(
        "clinical.Consultation", null=True, blank=True, on_delete=models.SET_NULL, related_name="billing_items"
    )
    lab_request = models.ForeignKey(
        "laboratory.LabRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="billing_items"
    )
    imaging_request = models.ForeignKey(
        "radiology.RadiologyRequest", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="billing_items",
    )
    admission = models.ForeignKey(
        "inpatient.Admission", null=True, blank=True, on_delete=models.SET_NULL, related_name="billing_items"
    )
    prescription_item = models.OneToOneField(
        "clinical.PrescriptionItem", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="billing_item",
    )

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        self.invoice.recalculate()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate()


class Payment(BaseModel):
    METHOD_CASH = "cash"
    METHOD_CARD = "card"
    METHOD_BANK = "bank"
    METHOD_MOBILE = "mobile_money"
    METHOD_MPESA = "mpesa"
    METHOD_INSURANCE = "insurance"
    METHOD_CREDIT = "credit"

    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_CARD, "Card"),
        (METHOD_BANK, "Bank Transfer"),
        (METHOD_MOBILE, "Mobile Money"),
        (METHOD_MPESA, "M-Pesa"),
        (METHOD_INSURANCE, "Insurance"),
        (METHOD_CREDIT, "Credit Transfer"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_REVERSED = "reversed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_REVERSED, "Reversed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    REFUND_STATUS_NONE = ""
    REFUND_STATUS_PENDING = "pending_approval"
    REFUND_STATUS_APPROVED = "approved"
    REFUND_STATUS_REJECTED = "rejected"

    REFUND_STATUS_CHOICES = [
        (REFUND_STATUS_NONE, "No Refund"),
        (REFUND_STATUS_PENDING, "Pending Approval"),
        (REFUND_STATUS_APPROVED, "Approved"),
        (REFUND_STATUS_REJECTED, "Rejected"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    payment_number = models.CharField(max_length=32, unique=True, editable=False, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=16, choices=METHOD_CHOICES, default=METHOD_CASH)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_COMPLETED)
    reference = models.CharField(max_length=64, blank=True)
    receipt_number = models.CharField(max_length=32, unique=True, editable=False)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    paid_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    insurance_provider = models.CharField(max_length=120, blank=True)
    policy_number = models.CharField(max_length=80, blank=True)
    member_name = models.CharField(max_length=120, blank=True)
    authorization_number = models.CharField(max_length=80, blank=True)
    insurance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    patient_copay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    mpesa_phone = models.CharField(max_length=20, blank=True)
    mpesa_transaction_code = models.CharField(max_length=64, blank=True)
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    refund_reason = models.TextField(blank=True)
    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default=REFUND_STATUS_NONE, blank=True)
    refund_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    refund_approved_at = models.DateTimeField(null=True, blank=True)
    reverse_reason = models.TextField(blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.payment_number or self.receipt_number} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            year = timezone.now().year
            last = (
                Payment.all_objects.filter(payment_number__startswith=f"PAY-{year}-")
                .order_by("-id").values_list("id", flat=True).first()
            )
            self.payment_number = f"PAY-{year}-{(last or 0) + 1:04d}"
        if not self.receipt_number:
            year = timezone.now().year
            last = (
                Payment.all_objects.filter(receipt_number__startswith=f"RCT-{year}-")
                .order_by("-id").values_list("id", flat=True).first()
            )
            self.receipt_number = f"RCT-{year}-{(last or 0) + 1:04d}"
        super().save(*args, **kwargs)
        if self.status == Payment.STATUS_COMPLETED:
            self.invoice.recalculate()


class PaymentGatewayTransaction(BaseModel):
    """Audit record for payment gateway interactions used during reconciliation."""

    PROVIDER_MPESA = "mpesa"
    PROVIDER_CARD = "card"
    PROVIDER_BANK = "bank"

    PROVIDER_CHOICES = [
        (PROVIDER_MPESA, "M-Pesa (Daraja)"),
        (PROVIDER_CARD, "Card Processor"),
        (PROVIDER_BANK, "Bank Feed"),
    ]

    STATUS_UNMATCHED = "unmatched"
    STATUS_MATCHED = "matched"
    STATUS_DISPUTED = "disputed"

    RECONCILIATION_CHOICES = [
        (STATUS_UNMATCHED, "Unmatched"),
        (STATUS_MATCHED, "Matched"),
        (STATUS_DISPUTED, "Disputed"),
    ]

    payment = models.ForeignKey(
        Payment, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="gateway_transactions",
    )
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES)
    provider_reference = models.CharField(max_length=128, db_index=True)
    provider_amount = models.DecimalField(max_digits=14, decimal_places=2)
    provider_timestamp = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    reconciliation_status = models.CharField(
        max_length=16, choices=RECONCILIATION_CHOICES, default=STATUS_UNMATCHED,
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.provider_reference} ({self.reconciliation_status})"
