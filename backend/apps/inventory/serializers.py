from rest_framework import serializers

from apps.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockMovement,
    Supplier,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "email", "address", "is_active"]


class InventoryItemSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id", "name", "category", "sku", "unit", "quantity", "reorder_level",
            "purchase_price", "selling_price", "supplier", "supplier_name", "location",
            "expiry_date", "is_active", "is_low_stock",
        ]
        read_only_fields = ["quantity"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "purchase_order", "item", "item_name", "quantity", "unit_price",
                  "received_quantity", "line_total"]
        read_only_fields = ["received_quantity", "line_total"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    items = PurchaseOrderItemSerializer(many=True, required=False)
    total_cost = serializers.DecimalField(read_only=True, max_digits=14, decimal_places=2)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "po_number", "supplier", "supplier_name", "status", "order_date",
                  "expected_date", "notes", "items", "total_cost"]
        read_only_fields = ["po_number", "status"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        po = PurchaseOrder.objects.create(**validated_data)
        for item in items:
            PurchaseOrderItem.objects.create(purchase_order=po, **item)
        return po


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = StockMovement
        fields = ["id", "item", "item_name", "movement_type", "quantity", "balance_after",
                  "reference", "notes", "performed_by", "performed_by_name", "created_at"]
        read_only_fields = ["balance_after", "performed_by", "created_at"]


class StockAdjustmentSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
