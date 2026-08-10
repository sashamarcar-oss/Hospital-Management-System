from django.conf import settings
from django.db import models


class MedicineCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    brand_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(
        MedicineCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="medicines"
    )
    manufacturer = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=32, default="unit", help_text="e.g. tablet, ml, vial, strip")
    strength = models.CharField(max_length=64, blank=True, help_text="e.g. 500mg")
    reorder_level = models.PositiveIntegerField(default=10)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    requires_prescription = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        return self.batches.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def is_low_stock(self):
        return self.total_stock <= self.reorder_level

    @property
    def earliest_expiry(self):
        batch = self.batches.exclude(expiry_date__isnull=True).order_by("expiry_date").first()
        return batch.expiry_date if batch else None


class MedicineBatch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expiry_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True)
    received_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date"]

    def __str__(self):
        return f"{self.medicine} batch {self.batch_number} x{self.quantity}"


class MedicineStockMovement(models.Model):
    """Audit trail of every stock change (receive, adjust, dispense, transfer, expire)."""

    MOVEMENT_RECEIVE = "receive"
    MOVEMENT_ADJUSTMENT = "adjustment"
    MOVEMENT_DISPENSE = "dispense"
    MOVEMENT_TRANSFER = "transfer"
    MOVEMENT_EXPIRE = "expire"
    MOVEMENT_RETURN = "return"

    MOVEMENT_CHOICES = [
        (MOVEMENT_RECEIVE, "Received"),
        (MOVEMENT_ADJUSTMENT, "Adjustment"),
        (MOVEMENT_DISPENSE, "Dispensed"),
        (MOVEMENT_TRANSFER, "Transferred"),
        (MOVEMENT_EXPIRE, "Expired"),
        (MOVEMENT_RETURN, "Returned"),
    ]

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="stock_movements")
    batch = models.ForeignKey(
        MedicineBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements"
    )
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_CHOICES)
    quantity = models.IntegerField(help_text="Positive = in, negative = out")
    balance_after = models.PositiveIntegerField(default=0)
    reference = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.medicine} {self.movement_type} {self.quantity}"
