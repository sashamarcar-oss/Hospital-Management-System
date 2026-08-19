from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import serializers

from apps.billing.models import (
    ChargeType,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentGatewayTransaction,
)
from apps.patients.serializers import PatientSummarySerializer
from apps.patients.models import Patient


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
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    patient_details = PatientSummarySerializer(source="invoice.patient", read_only=True)
    idempotency_key = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    payment_number = serializers.CharField(read_only=True)
    reversed_by_name = serializers.CharField(source="reversed_by.get_full_name", read_only=True)
    refund_approved_by_name = serializers.CharField(source="refund_approved_by.get_full_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "payment_number", "invoice", "invoice_number", "patient_details",
            "amount", "method", "status", "reference", "receipt_number",
            "received_by", "received_by_name", "paid_at", "notes", "idempotency_key",
            "insurance_provider", "policy_number", "member_name", "authorization_number",
            "insurance_amount", "patient_copay", "mpesa_phone", "mpesa_transaction_code",
            "refund_amount", "refund_reason", "refund_status", "refund_approved_by",
            "refund_approved_by_name", "refund_approved_at",
            "reverse_reason", "reversed_by", "reversed_by_name", "reversed_at",
        ]
        read_only_fields = [
            "payment_number", "receipt_number", "received_by", "paid_at",
            "refund_amount", "refund_reason", "refund_status",
            "refund_approved_by", "refund_approved_at",
            "reverse_reason", "reversed_by", "reversed_at",
        ]
        validators = []

    def validate(self, attrs):
        invoice = attrs.get("invoice") or (self.instance.invoice if self.instance else None)
        amount = attrs.get("amount") or (self.instance.amount if self.instance else Decimal("0"))
        if amount <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero."})

        if invoice and invoice.status == Invoice.STATUS_CANCELLED:
            raise serializers.ValidationError({"invoice": "Cannot make payment against a cancelled invoice."})
        
        # Invoice must have a positive total to accept payments
        if invoice and invoice.total <= 0:
            raise serializers.ValidationError({
                "invoice": "Payment cannot be recorded because this invoice has no billable items."
            })
        
        if invoice and invoice.status == Invoice.STATUS_PAID and (not self.instance):
            raise serializers.ValidationError({"invoice": "This invoice is already fully paid."})

        # Overpayments are supported as customer credit. A payment is valid as long as it is
        # positive and the invoice is not cancelled or already fully settled for a new payment.
        if invoice and not self.instance and invoice.balance <= 0 and invoice.total > 0:
            # If the invoice is already settled, no new payment should be created unless this is
            # explicitly a credit adjustment workflow. Keep the project’s credit model intact.
            if invoice.status == Invoice.STATUS_PAID:
                raise serializers.ValidationError({"invoice": "This invoice is already fully paid."})

        method = attrs.get("method", getattr(self.instance, "method", None))
        if method == Payment.METHOD_INSURANCE:
            if not attrs.get("insurance_provider", getattr(self.instance, "insurance_provider", "")):
                raise serializers.ValidationError({"insurance_provider": "Insurance provider is required."})
            ins_amount = Decimal(str(attrs.get("insurance_amount", 0) or 0))
            copay = Decimal(str(attrs.get("patient_copay", 0) or 0))
            if ins_amount + copay not in (Decimal("0"), Decimal(str(amount))):
                raise serializers.ValidationError(
                    {"insurance_amount": "Insurance amount plus patient co-pay must equal the payment amount."}
                )
            if invoice and invoice.insurance_claim:
                from apps.insurance.models import InsuranceClaim
                if invoice.insurance_claim.status not in (
                    InsuranceClaim.STATUS_APPROVED,
                    InsuranceClaim.STATUS_PARTIALLY_APPROVED,
                    InsuranceClaim.STATUS_PAID,
                ):
                    raise serializers.ValidationError({
                        "invoice": "Linked insurance claim must be approved before logging an insurance payment.",
                    })

        if method == Payment.METHOD_MPESA:
            if not (attrs.get("mpesa_phone", getattr(self.instance, "mpesa_phone", ""))
                    and attrs.get("mpesa_transaction_code", getattr(self.instance, "mpesa_transaction_code", ""))):
                raise serializers.ValidationError(
                    {"mpesa_transaction_code": "M-Pesa phone number and transaction code are required."}
                )

        if method in (Payment.METHOD_CARD, Payment.METHOD_BANK) and not attrs.get("reference", getattr(self.instance, "reference", "")):
            raise serializers.ValidationError(
                {"reference": "Transaction reference is required for card and bank transfer payments."}
            )

        return attrs

    def create(self, validated_data):
        idempotency_key = validated_data.get("idempotency_key")
        if idempotency_key:
            existing = Payment.all_objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        invoice = validated_data["invoice"]

        with transaction.atomic():
            locked_invoice = Invoice.all_objects.select_for_update().get(pk=invoice.pk)

            validated_data["invoice"] = locked_invoice
            payment = Payment.objects.create(
                **validated_data,
                received_by=self.context["request"].user,
            )
            locked_invoice.recalculate()

            if payment.method == Payment.METHOD_INSURANCE:
                locked_invoice.insurance_covered_amount += payment.insurance_amount
                locked_invoice.patient_copay_amount += payment.patient_copay
                locked_invoice.save(update_fields=["insurance_covered_amount", "patient_copay_amount"])

        return payment


class PaymentStatsSerializer(serializers.Serializer):
    today_collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_payments = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_count = serializers.IntegerField()
    mpesa_collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    cash_collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    card_collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    bank_collection = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class PaymentGatewayTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGatewayTransaction
        fields = [
            "id", "payment", "provider", "provider_reference", "provider_amount",
            "provider_timestamp", "raw_response", "reconciliation_status",
            "reconciled_at", "reconciled_by", "notes",
        ]
        read_only_fields = [
            "reconciliation_status", "reconciled_at", "reconciled_by",
        ]


class InvoiceCreateItemSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1, default=1)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    charge_type = serializers.PrimaryKeyRelatedField(
        queryset=ChargeType.objects.all(), required=False, allow_null=True,
    )


class InvoiceCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0, required=False)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=0, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = InvoiceCreateItemSerializer(many=True)

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one billable item is required.")
        return items

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        request = self.context["request"]

        with transaction.atomic():
            invoice = Invoice.objects.create(
                patient=validated_data["patient"],
                discount=validated_data.get("discount", Decimal("0")),
                tax_rate=validated_data.get("tax_rate", Decimal("0")),
                due_date=validated_data.get("due_date"),
                notes=validated_data.get("notes", ""),
                issued_by=request.user,
                created_by=request.user,
            )

            for item_data in items_data:
                qty = item_data.get("quantity", 1)
                price = item_data["unit_price"]
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=item_data["description"],
                    quantity=qty,
                    unit_price=price,
                    charge_type=item_data.get("charge_type"),
                    created_by=request.user,
                )

            invoice.recalculate()

        return invoice


class InvoiceSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.get_full_name", read_only=True)
    patient_credit = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id", "patient", "patient_details", "invoice_number", "status", "subtotal",
            "discount", "tax_rate", "tax", "total", "amount_paid", "balance",
            "insurance_covered_amount", "patient_copay_amount", "due_date",
            "insurance_claim", "notes", "issued_by", "issued_by_name", "issued_at",
            "items", "payments", "patient_credit",
        ]
        read_only_fields = [
            "invoice_number", "status", "subtotal", "tax", "total", "amount_paid",
            "balance", "issued_at", "insurance_covered_amount", "patient_copay_amount",
        ]

    def get_patient_credit(self, obj):
        return str(Invoice.patient_credit(obj.patient, exclude_pk=obj.pk))

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            if "amount" in self.initial_data:
                raise serializers.ValidationError(
                    {"amount": "Invoice amount cannot be set manually. "
                     "It is calculated automatically from invoice items."}
                )
        return attrs
