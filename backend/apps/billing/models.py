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

    STATUS_CHOICES = [
        (STATUS_UNPAID, "Unpaid"),
        (STATUS_PARTIALLY_PAID, "Partially Paid"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=32, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_UNPAID)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
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
        from decimal import Decimal

        if self.pk:
            items = self.items.all()
            subtotal = sum((i.line_total for i in items), Decimal("0"))
        else:
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
        if self.balance < 0:
            self.balance = Decimal("0")
        if self.status != self.STATUS_CANCELLED:
            if self.balance == 0 and self.total > 0:
                self.status = self.STATUS_PAID
            elif self.amount_paid > 0:
                self.status = self.STATUS_PARTIALLY_PAID
            else:
                if self.due_date and self.due_date < timezone.now().date():
                    self.status = self.STATUS_OVERDUE
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


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    charge_type = models.ForeignKey(
        ChargeType, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_items"
    )
    # Optional references to source records for automatic charge generation.
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
    METHOD_INSURANCE = "insurance"

    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_CARD, "Card"),
        (METHOD_BANK, "Bank Transfer"),
        (METHOD_MOBILE, "Mobile Money"),
        (METHOD_INSURANCE, "Insurance"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
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

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"

    def save(self, *args, **kwargs):
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
