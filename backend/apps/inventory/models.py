from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Supplier(BaseModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InventoryItem(BaseModel):
    CATEGORY_CHOICES = [
        ("medical_supplies", "Medical Supplies"),
        ("consumables", "Consumables"),
        ("equipment", "Equipment"),
        ("ppe", "PPE"),
        ("stationery", "Stationery"),
        ("other", "Other Supplies"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="other")
    sku = models.CharField(max_length=64, blank=True)
    unit = models.CharField(max_length=32, default="unit")
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL, related_name="items")
    location = models.CharField(max_length=120, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level


class PurchaseOrder(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_ORDERED = "ordered"
    STATUS_PARTIALLY_RECEIVED = "partially_received"
    STATUS_RECEIVED = "received"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ORDERED, "Ordered"),
        (STATUS_PARTIALLY_RECEIVED, "Partially Received"),
        (STATUS_RECEIVED, "Received"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    po_number = models.CharField(max_length=32, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="purchase_orders")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-order_date"]

    def __str__(self):
        return self.po_number

    def save(self, *args, **kwargs):
        if not self.po_number:
            year = timezone.now().year
            last = (
                PurchaseOrder.all_objects.filter(po_number__startswith=f"PO-{year}-")
                .order_by("-id").values_list("id", flat=True).first()
            )
            self.po_number = f"PO-{year}-{(last or 0) + 1:04d}"
        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        return sum(item.line_total for item in self.items.all())


class PurchaseOrderItem(BaseModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="po_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    received_quantity = models.PositiveIntegerField(default=0)
    line_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class StockMovement(BaseModel):
    MOVEMENT_RECEIVE = "receive"
    MOVEMENT_ADJUSTMENT = "adjustment"
    MOVEMENT_ISSUE = "issue"
    MOVEMENT_TRANSFER = "transfer"
    MOVEMENT_EXPIRE = "expire"

    MOVEMENT_CHOICES = [
        (MOVEMENT_RECEIVE, "Received"),
        (MOVEMENT_ADJUSTMENT, "Adjustment"),
        (MOVEMENT_ISSUE, "Issued"),
        (MOVEMENT_TRANSFER, "Transferred"),
        (MOVEMENT_EXPIRE, "Expired"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_movements")
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_CHOICES)
    quantity = models.IntegerField()
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
        return f"{self.item} {self.movement_type} {self.quantity}"
