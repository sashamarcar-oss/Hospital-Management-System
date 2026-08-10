from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.billing.models import ChargeType, Invoice, Payment
from apps.billing.serializers import (
    ChargeTypeSerializer,
    InvoiceSerializer,
    PaymentSerializer,
)
from apps.core.models import AuditLog
from apps.core.services import audit_log


class ChargeTypeViewSet(viewsets.ModelViewSet):
    queryset = ChargeType.objects.all()
    serializer_class = ChargeTypeSerializer
    permission_classes = [HasPermission]
    code = "billing.view"
    write_code = "billing.update"
    search_fields = ["name", "code"]
    filterset_fields = ["category", "is_active"]
    pagination_class = None


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("patient").prefetch_related("items", "payments").all()
    serializer_class = InvoiceSerializer
    permission_classes = [HasPermission]
    code = "billing.view"
    write_code = "billing.update"
    filterset_fields = ["status", "patient", "insurance_claim"]
    search_fields = ["invoice_number", "patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["issued_at", "total", "balance"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        invoice = serializer.save(issued_by=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "billing.invoice",
                  record=invoice.invoice_number, object_id=invoice.id,
                  request=self.request, new_value=serializer.data)

    def perform_update(self, serializer):
        invoice = serializer.save(updated_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_UPDATE, "billing.invoice",
                  record=invoice.invoice_number, object_id=invoice.id,
                  request=self.request, new_value=serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.STATUS_CANCELLED:
            return Response({"detail": "Invoice already cancelled."}, status=400)
        previous = {"status": invoice.status}
        invoice.status = Invoice.STATUS_CANCELLED
        invoice.save(update_fields=["status"])
        audit_log(request.user, AuditLog.ACTION_UPDATE, "billing.invoice",
                  record=invoice.invoice_number, object_id=invoice.id, request=request,
                  previous_value=previous, new_value={"status": invoice.status},
                  description="invoice cancelled")
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        qs = self.get_queryset().filter(
            status=Invoice.STATUS_UNPAID, due_date__lt=timezone.now().date()
        )
        for invoice in qs:
            if invoice.status == Invoice.STATUS_UNPAID:
                invoice.status = Invoice.STATUS_OVERDUE
                invoice.save(update_fields=["status"])
        qs = self.get_queryset().filter(status=Invoice.STATUS_OVERDUE)
        return Response(InvoiceSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset()
        totals = qs.aggregate(
            total_revenue=Sum("total"),
            total_paid=Sum("amount_paid"),
            outstanding=Sum("balance"),
        )
        return Response(totals)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice__patient", "received_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [HasPermission]
    code = "payments.receive_payment"
    filterset_fields = ["invoice", "method", "status", "invoice__patient"]
    search_fields = ["receipt_number", "reference", "invoice__invoice_number"]
    ordering_fields = ["paid_at", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(invoice__patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        payment = serializer.save()
        audit_log(self.request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.receipt_number, object_id=payment.id,
                  request=self.request, new_value=serializer.data,
                  description=f"payment of {payment.amount} on {payment.invoice.invoice_number}")

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        payment = self.get_object()
        if payment.status != Payment.STATUS_COMPLETED:
            return Response({"detail": "Only completed payments can be refunded."}, status=400)
        previous = {"status": payment.status}
        payment.status = Payment.STATUS_REFUNDED
        payment.save(update_fields=["status"])
        payment.invoice.recalculate()
        audit_log(request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.receipt_number, object_id=payment.id, request=request,
                  previous_value=previous, new_value={"status": payment.status},
                  description="payment refunded")
        return Response(PaymentSerializer(payment).data)
