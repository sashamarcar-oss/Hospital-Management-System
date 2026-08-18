from django.contrib import admin

from apps.billing.models import (
    ChargeType,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentGatewayTransaction,
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ["line_total"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number", "patient", "status", "total", "amount_paid",
        "balance", "issued_at",
    ]
    list_filter = ["status", "issued_at"]
    search_fields = ["invoice_number", "patient__first_name", "patient__last_name"]
    inlines = [InvoiceItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "payment_number", "receipt_number", "invoice", "amount", "method", "status",
        "refund_status", "paid_at",
    ]
    list_filter = ["method", "status", "refund_status"]
    search_fields = ["payment_number", "receipt_number", "reference", "invoice__invoice_number"]
    readonly_fields = [
        "payment_number", "receipt_number", "refund_approved_by", "refund_approved_at",
        "reversed_by", "reversed_at", "reverse_reason",
    ]


@admin.register(ChargeType)
class ChargeTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "category", "default_price", "is_active"]
    list_filter = ["category", "is_active"]


@admin.register(PaymentGatewayTransaction)
class PaymentGatewayTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "provider", "provider_reference", "provider_amount",
        "reconciliation_status", "payment", "reconciled_at",
    ]
    list_filter = ["provider", "reconciliation_status"]
    search_fields = ["provider_reference", "payment__receipt_number"]
    readonly_fields = ["reconciled_at", "reconciled_by"]
