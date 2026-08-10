from rest_framework import serializers

from apps.pharmacy.models import (
    Medicine,
    MedicineBatch,
    MedicineCategory,
    MedicineStockMovement,
)


class MedicineCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineCategory
        fields = ["id", "name"]


class MedicineBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineBatch
        fields = ["id", "medicine", "batch_number", "quantity", "purchase_price", "expiry_date", "supplier", "received_at"]
        read_only_fields = ["received_at"]


class MedicineSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    earliest_expiry = serializers.DateField(read_only=True)
    batches = MedicineBatchSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=MedicineCategory.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Medicine
        fields = [
            "id", "name", "generic_name", "brand_name", "category", "category_name",
            "manufacturer", "unit", "strength", "reorder_level", "purchase_price",
            "selling_price", "requires_prescription", "is_active", "total_stock",
            "is_low_stock", "earliest_expiry", "batches", "created_at",
        ]


class MedicineStockInSerializer(serializers.Serializer):
    batch_number = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    expiry_date = serializers.DateField(required=False)
    supplier = serializers.CharField(required=False, allow_blank=True)


class StockAdjustmentSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)
    batch_id = serializers.PrimaryKeyRelatedField(
        queryset=MedicineBatch.objects.all(), required=False, allow_null=True
    )


class MedicineStockMovementSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True)
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)

    class Meta:
        model = MedicineStockMovement
        fields = [
            "id", "medicine", "medicine_name", "batch", "batch_number", "movement_type",
            "quantity", "balance_after", "reference", "notes", "performed_by", "performed_by_name",
            "created_at",
        ]
        read_only_fields = ["balance_after", "performed_by", "created_at"]
