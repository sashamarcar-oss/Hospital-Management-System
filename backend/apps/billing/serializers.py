from rest_framework import serializers

from apps.billing.models import ChargeType, Invoice, InvoiceItem, Payment
from apps.patients.serializers import PatientSummarySerializer


class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = ["id", "name", "code", "category", "default_price", "is_active"]


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "invoice", "description", "quantity", "unit_price", "line_total",
                  "charge_type", "consultation", "lab_request", "imaging_request",
                  "admission", "prescription_item"]
        read_only_fields = ["line_total"]

    def create(self, validated_data):
        item = InvoiceItem.objects.create(**validated_data)
        item.invoice.recalculate()
        return item


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source="received_by.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "invoice", "amount", "method", "status", "reference",
                  "receipt_number", "received_by", "received_by_name", "paid_at", "notes"]
        read_only_fields = ["receipt_number", "received_by", "paid_at"]

    def validate(self, attrs):
        invoice = attrs.get("invoice") or (self.instance.invoice if self.instance else None)
        amount = attrs.get("amount") or (self.instance.amount if self.instance else 0)
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})
        if amount > invoice.balance:
            raise serializers.ValidationError(
                {"amount": f"Amount exceeds the invoice balance of {invoice.balance}."}
            )
        return attrs

    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data, received_by=self.context["request"].user)
        payment.invoice.recalculate()
        return payment


class InvoiceSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.get_full_name", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "patient", "patient_details", "invoice_number", "status", "subtotal",
            "discount", "tax_rate", "tax", "total", "amount_paid", "balance", "due_date",
            "insurance_claim", "notes", "issued_by", "issued_by_name", "issued_at",
            "items", "payments",
        ]
        read_only_fields = [
            "invoice_number", "status", "subtotal", "tax", "total", "amount_paid",
            "balance", "issued_at",
        ]

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value
