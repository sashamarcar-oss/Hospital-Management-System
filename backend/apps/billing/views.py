from decimal import Decimal

from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.billing.models import ChargeType, Invoice, Payment, PaymentGatewayTransaction
from apps.billing.serializers import (
    ChargeTypeSerializer,
    InvoiceSerializer,
    PaymentGatewayTransactionSerializer,
    PaymentSerializer,
)
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify


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
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
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

    @action(detail=True, methods=["get"], url_path="pdf")
    def invoice_pdf(self, request, pk=None):
        invoice = self.get_object()
        from apps.billing.pdf import build_invoice_pdf

        buffer = build_invoice_pdf(invoice)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{invoice.invoice_number}.pdf"'
        )
        return response


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice__patient", "received_by", "reversed_by", "refund_approved_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [HasPermission]
    code = "payments.view"
    write_code = "payments.receive_payment"
    create_code = "payments.receive_payment"
    filterset_fields = ["invoice", "method", "status", "invoice__patient"]
    search_fields = [
        "payment_number", "receipt_number", "reference",
        "invoice__invoice_number", "invoice__patient__first_name",
        "invoice__patient__last_name", "invoice__patient__patient_number",
        "mpesa_transaction_code", "mpesa_phone",
    ]
    ordering_fields = ["paid_at", "amount", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(invoice__patient=linked) if linked else qs.none()
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(invoice__patient_id=patient_id)
        method = self.request.query_params.get("method")
        if method:
            qs = qs.filter(method=method)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(paid_at__date__gte=date_from)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(paid_at__date__lte=date_to)
        received_by = self.request.query_params.get("received_by")
        if received_by:
            qs = qs.filter(received_by_id=received_by)
        return qs

    def perform_create(self, serializer):
        payment = serializer.save()
        invoice = payment.invoice
        audit_log(self.request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.payment_number, object_id=payment.id,
                  request=self.request, new_value=PaymentSerializer(payment).data,
                  description=f"payment of {payment.amount} on {invoice.invoice_number}")
        try:
            patient_user = invoice.patient.user
            if patient_user:
                notify(
                    patient_user,
                    "Payment Received",
                    f"Your payment of KES {payment.amount:,.2f} for invoice {invoice.invoice_number} has been received. Receipt: {payment.receipt_number}",
                    notification_type="payment",
                    link=f"/billing/{invoice.id}",
                    related_module="billing",
                    related_object_id=payment.id,
                )
        except Exception:
            pass

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        payment = self.get_object()
        if payment.status != Payment.STATUS_COMPLETED:
            return Response({"detail": "Only completed payments can be reversed."}, status=400)

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response({"detail": "Reversal reason is required."}, status=400)

        previous = {
            "status": payment.status,
            "amount": str(payment.amount),
        }

        payment.status = Payment.STATUS_REVERSED
        payment.reverse_reason = reason
        payment.reversed_by = request.user
        payment.reversed_at = timezone.now()
        payment.save(update_fields=[
            "status", "reverse_reason", "reversed_by", "reversed_at",
        ])

        invoice = payment.invoice
        if payment.method == Payment.METHOD_INSURANCE and payment.insurance_amount:
            invoice.insurance_covered_amount = max(
                Decimal("0"), invoice.insurance_covered_amount - payment.insurance_amount,
            )
            invoice.patient_copay_amount = max(
                Decimal("0"), invoice.patient_copay_amount - payment.patient_copay,
            )
            invoice.save(update_fields=["insurance_covered_amount", "patient_copay_amount"])

        invoice.recalculate()

        audit_log(request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.payment_number, object_id=payment.id, request=request,
                  previous_value=previous,
                  new_value={"status": "reversed", "reverse_reason": reason},
                  description=f"payment of {payment.amount} reversed")

        try:
            patient_user = invoice.patient.user
            if patient_user:
                notify(
                    patient_user,
                    "Payment Reversed",
                    f"Your payment of KES {payment.amount:,.2f} (Receipt: {payment.receipt_number}) has been reversed. Reason: {reason}",
                    notification_type="payment",
                    link=f"/billing/{invoice.id}",
                    related_module="billing",
                    related_object_id=payment.id,
                )
        except Exception:
            pass

        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        payment = self.get_object()
        if payment.status != Payment.STATUS_COMPLETED:
            return Response({"detail": "Only completed payments can be refunded."}, status=400)
        if payment.refund_status == Payment.REFUND_STATUS_PENDING:
            return Response({"detail": "Refund already pending approval."}, status=400)
        if payment.refund_status == Payment.REFUND_STATUS_APPROVED:
            return Response({"detail": "Payment has already been refunded."}, status=400)

        refund_amount = Decimal(str(request.data.get("amount", payment.amount)))
        reason = request.data.get("reason", "").strip()

        if refund_amount <= 0:
            return Response({"detail": "Refund amount must be greater than zero."}, status=400)
        if refund_amount > payment.amount:
            return Response({"detail": "Refund amount cannot exceed the original payment amount."}, status=400)
        if not reason:
            return Response({"detail": "Refund reason is required."}, status=400)

        previous = {
            "status": payment.status,
            "refund_amount": str(payment.refund_amount),
            "refund_status": payment.refund_status,
        }
        payment.refund_amount = refund_amount
        payment.refund_reason = reason
        payment.refund_status = Payment.REFUND_STATUS_PENDING
        payment.save(update_fields=["refund_amount", "refund_reason", "refund_status"])
        audit_log(request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.payment_number, object_id=payment.id, request=request,
                  previous_value=previous,
                  new_value={"refund_amount": str(refund_amount), "refund_status": "pending_approval"},
                  description=f"refund of {refund_amount} pending approval")
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def approve_refund(self, request, pk=None):
        payment = self.get_object()
        if payment.refund_status != Payment.REFUND_STATUS_PENDING:
            return Response({"detail": "No pending refund to approve."}, status=400)

        previous = {"status": payment.status, "refund_status": payment.refund_status}
        payment.status = Payment.STATUS_REFUNDED
        payment.refund_status = Payment.REFUND_STATUS_APPROVED
        payment.refund_approved_by = request.user
        payment.refund_approved_at = timezone.now()
        payment.save(update_fields=[
            "status", "refund_status", "refund_approved_by", "refund_approved_at",
        ])

        invoice = payment.invoice
        if payment.method == Payment.METHOD_INSURANCE and payment.insurance_amount:
            invoice.insurance_covered_amount = max(
                Decimal("0"), invoice.insurance_covered_amount - payment.insurance_amount,
            )
            invoice.patient_copay_amount = max(
                Decimal("0"), invoice.patient_copay_amount - payment.patient_copay,
            )
            invoice.save(update_fields=["insurance_covered_amount", "patient_copay_amount"])

        invoice.recalculate()
        audit_log(request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.payment_number, object_id=payment.id, request=request,
                  previous_value=previous,
                  new_value={"status": "refunded", "refund_status": "approved"},
                  description=f"refund of {payment.refund_amount} approved")

        try:
            patient_user = invoice.patient.user
            if patient_user:
                notify(
                    patient_user,
                    "Refund Processed",
                    f"Your refund of KES {payment.refund_amount:,.2f} for invoice {invoice.invoice_number} has been approved and processed.",
                    notification_type="payment",
                    link=f"/billing/{invoice.id}",
                    related_module="billing",
                    related_object_id=payment.id,
                )
        except Exception:
            pass

        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["post"])
    def reject_refund(self, request, pk=None):
        payment = self.get_object()
        if payment.refund_status != Payment.REFUND_STATUS_PENDING:
            return Response({"detail": "No pending refund to reject."}, status=400)

        previous = {"refund_status": payment.refund_status}
        payment.refund_status = Payment.REFUND_STATUS_REJECTED
        payment.save(update_fields=["refund_status"])
        audit_log(request.user, AuditLog.ACTION_PAYMENT, "billing.payment",
                  record=payment.payment_number, object_id=payment.id, request=request,
                  previous_value=previous,
                  new_value={"refund_status": "rejected"},
                  description="refund rejected")
        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["get"], url_path="receipt-pdf")
    def receipt_pdf(self, request, pk=None):
        payment = self.get_object()
        from apps.billing.pdf import build_receipt_pdf

        buffer = build_receipt_pdf(payment)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{payment.receipt_number}.pdf"'
        )
        return response

    @action(detail=False, methods=["get"], url_path="stats")
    def payment_stats(self, request):
        today = timezone.now().date()
        completed = Payment.objects.filter(status=Payment.STATUS_COMPLETED)

        today_collection = completed.filter(paid_at__date=today).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        total_payments = completed.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        total_count = completed.count()

        mpesa_collection = completed.filter(
            method__in=[Payment.METHOD_MPESA, Payment.METHOD_MOBILE]
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        cash_collection = completed.filter(method=Payment.METHOD_CASH).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        card_collection = completed.filter(method=Payment.METHOD_CARD).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        bank_collection = completed.filter(method=Payment.METHOD_BANK).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        outstanding = Invoice.objects.filter(
            status__in=[Invoice.STATUS_UNPAID, Invoice.STATUS_PARTIALLY_PAID, Invoice.STATUS_OVERDUE]
        ).aggregate(total=Sum("balance"))["total"] or Decimal("0")

        return Response({
            "today_collection": str(round(today_collection, 2)),
            "total_payments": str(round(total_payments, 2)),
            "total_count": total_count,
            "mpesa_collection": str(round(mpesa_collection, 2)),
            "cash_collection": str(round(cash_collection, 2)),
            "card_collection": str(round(card_collection, 2)),
            "bank_collection": str(round(bank_collection, 2)),
            "outstanding_balance": str(round(outstanding, 2)),
        })


class PaymentGatewayTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentGatewayTransaction.objects.select_related("payment", "reconciled_by").all()
    serializer_class = PaymentGatewayTransactionSerializer
    permission_classes = [HasPermission]
    code = "payments.view"
    write_code = "payments.receive_payment"
    create_code = "payments.receive_payment"
    filterset_fields = ["provider", "reconciliation_status", "payment"]
    search_fields = ["provider_reference", "payment__receipt_number"]
    ordering_fields = ["created_at", "provider_amount"]

    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        gateway_tx = self.get_object()
        if gateway_tx.reconciliation_status != PaymentGatewayTransaction.STATUS_UNMATCHED:
            return Response(
                {"detail": "Transaction is already reconciled or disputed."},
                status=400,
            )

        payment_id = request.data.get("payment")
        notes = request.data.get("notes", "")

        if payment_id:
            try:
                payment = Payment.objects.get(pk=payment_id)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=404)

            if payment.amount != gateway_tx.provider_amount:
                return Response(
                    {"detail": f"Amount mismatch: payment={payment.amount}, gateway={gateway_tx.provider_amount}"},
                    status=400,
                )

            gateway_tx.payment = payment
            gateway_tx.reconciliation_status = PaymentGatewayTransaction.STATUS_MATCHED
        else:
            gateway_tx.reconciliation_status = PaymentGatewayTransaction.STATUS_DISPUTED

        gateway_tx.reconciled_at = timezone.now()
        gateway_tx.reconciled_by = request.user
        gateway_tx.notes = notes
        gateway_tx.save(update_fields=[
            "payment", "reconciliation_status", "reconciled_at", "reconciled_by", "notes",
        ])

        return Response(PaymentGatewayTransactionSerializer(gateway_tx).data)
