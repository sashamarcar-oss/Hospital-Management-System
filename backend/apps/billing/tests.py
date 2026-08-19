"""Comprehensive tests for the billing module.

Covers: access control, transaction safety, refunds, insurance claim validation,
idempotency, credit/overpayment, and PDF generation.
"""

from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role
from apps.billing.models import (
    Invoice,
    InvoiceItem,
    Payment,
    PaymentGatewayTransaction,
)
from apps.patients.models import Patient

User = get_user_model()


def create_role(role_code, permissions=()):
    role, _ = Role.objects.get_or_create(code=role_code, defaults={"name": role_code})
    for code in permissions:
        module, action = code.split(".", 1)
        perm, _ = Permission.objects.get_or_create(
            code=code, defaults={"name": code, "module": module},
        )
        role.permissions.add(perm)
    return role


def create_user(username, role_code, permissions=()):
    role = create_role(role_code, permissions)
    user = User.objects.create_user(username=username, password="test1234", role=role)
    return user


class BillingBaseTestCase(APITestCase):
    def setUp(self):
        self.accountant = create_user(
            "accountant1", "accountant",
            permissions=[
                "billing.view", "billing.update", "billing.create", "billing.delete",
                "payments.view", "payments.receive_payment",
            ],
        )
        self.admin_user = create_user(
            "admin1", "admin",
            permissions=[
                "billing.view", "billing.update", "billing.create",
                "payments.view", "payments.receive_payment",
            ],
        )
        self.patient_user = create_user(
            "patient1", "patient", permissions=["billing.view", "payments.view"],
        )
        self.receptionist = create_user(
            "reception1", "receptionist",
            permissions=["billing.view", "billing.create", "payments.view"],
        )
        self.superadmin = User.objects.create_superuser(
            username="superadmin", password="test1234", email="sa@test.com",
        )

        self.patient = Patient.objects.create(
            first_name="Jane", last_name="Doe",
            date_of_birth=timezone.now().date().replace(year=1990),
            gender="female", phone="0712000000",
        )
        self.patient.user = self.patient_user
        self.patient.save()

        self.patient2 = Patient.objects.create(
            first_name="John", last_name="Smith",
            date_of_birth=timezone.now().date().replace(year=1985),
            gender="male", phone="0722000000",
        )

        self.invoice = Invoice.objects.create(
            patient=self.patient, issued_by=self.accountant,
        )
        InvoiceItem.objects.create(
            invoice=self.invoice, description="Consultation", quantity=1,
            unit_price=Decimal("1000.00"),
        )
        self.invoice.recalculate()

        self.invoice2 = Invoice.objects.create(
            patient=self.patient2, issued_by=self.accountant,
        )
        InvoiceItem.objects.create(
            invoice=self.invoice2, description="Lab Test", quantity=2,
            unit_price=Decimal("500.00"),
        )
        self.invoice2.recalculate()

    def _auth(self, user):
        self.client.force_authenticate(user=user)


class InvoiceBusinessLogicTests(BillingBaseTestCase):
    """Invoice creation and payment state must be computed from actual payments."""

    def test_new_invoice_starts_unpaid_with_full_balance(self):
        self._auth(self.accountant)
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.accountant)
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=1,
            unit_price=Decimal("10000.00"),
        )
        invoice.refresh_from_db()

        self.assertEqual(invoice.total, Decimal("10000.00"))
        self.assertEqual(invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(invoice.balance, Decimal("10000.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_UNPAID)

    def test_partial_and_final_payment_update_status_and_balance(self):
        self._auth(self.accountant)
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.accountant)
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=1,
            unit_price=Decimal("10000.00"),
        )
        invoice.refresh_from_db()

        payment1 = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "3000.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(payment1.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("3000.00"))
        self.assertEqual(invoice.balance, Decimal("7000.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_PARTIALLY_PAID)

        payment2 = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "7000.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(payment2.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("10000.00"))
        self.assertEqual(invoice.balance, Decimal("0.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_PAID)

    def test_outstanding_invoice_api_excludes_paid_invoices(self):
        self._auth(self.accountant)
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.accountant)
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=1,
            unit_price=Decimal("10000.00"),
        )
        invoice.refresh_from_db()

        resp = self.client.get("/api/billing/outstanding/", {"patient_id": self.patient.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invoice_ids = [entry["id"] for entry in resp.data]
        self.assertIn(invoice.id, invoice_ids)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("10000.00"),
            method="cash",
            status=Payment.STATUS_COMPLETED,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.STATUS_PAID)

        resp = self.client.get("/api/billing/outstanding/", {"patient_id": self.patient.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invoice_ids_after_payment = [entry["id"] for entry in resp.data]
        self.assertNotIn(invoice.id, invoice_ids_after_payment)


# ---------------------------------------------------------------------------
# Issue 1: Access Control
# ---------------------------------------------------------------------------

class PaymentAccessControlTests(BillingBaseTestCase):
    """PaymentViewSet must allow view access for roles with payments.view."""

    def test_accountant_can_list_payments(self):
        self._auth(self.accountant)
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_patient_can_view_own_payments(self):
        Payment.objects.create(
            invoice=self.invoice, amount=Decimal("500.00"),
            method="cash", status="completed",
        )
        self._auth(self.patient_user)
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_patient_cannot_view_other_patient_payments(self):
        Payment.objects.create(
            invoice=self.invoice2, amount=Decimal("500.00"),
            method="cash", status="completed",
        )
        self._auth(self.patient_user)
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_unauthenticated_cannot_list_payments(self):
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_payments_view_cannot_list(self):
        user = create_user("noview", "nurse", permissions=["patients.view"])
        self._auth(user)
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_view_payments(self):
        self._auth(self.receptionist)
        resp = self.client.get("/api/billing/payments/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Issue 2: Transaction Safety
# ---------------------------------------------------------------------------

class PaymentTransactionSafetyTests(BillingBaseTestCase):
    """Payments must use select_for_update to prevent race conditions."""

    def test_payment_updates_invoice_balance(self):
        self._auth(self.accountant)
        self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "400.00",
            "method": "cash",
        }, format="json")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.balance, Decimal("600.00"))
        self.assertEqual(self.invoice.status, Invoice.STATUS_PARTIALLY_PAID)

    def test_payment_exactly_balance_succeeds(self):
        self._auth(self.accountant)
        resp = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1000.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.balance, Decimal("0.00"))

    def test_concurrent_payments_prevented_by_select_for_update(self):
        import inspect
        from apps.billing.serializers import PaymentSerializer
        source = inspect.getsource(PaymentSerializer.create)
        self.assertIn("select_for_update", source)
        self.assertIn("transaction.atomic", source)


# ---------------------------------------------------------------------------
# Issue 3: Refund Workflow
# ---------------------------------------------------------------------------

class RefundWorkflowTests(BillingBaseTestCase):
    """Partial refund, reason, approval, and insurance reversal."""

    def setUp(self):
        super().setUp()
        self.payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("1000.00"),
            method="cash", status="completed",
        )

    def test_full_refund_requires_reason(self):
        self._auth(self.accountant)
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/refund/",
            {"reason": ""}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_refund_pending_approval(self):
        self._auth(self.accountant)
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/refund/",
            {"amount": "500.00", "reason": "Service not rendered"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.refund_status, "pending_approval")
        self.assertEqual(self.payment.refund_amount, Decimal("500.00"))
        self.assertEqual(self.payment.status, "completed")

    def test_approve_refund_updates_status(self):
        self._auth(self.accountant)
        self.client.post(
            f"/api/billing/payments/{self.payment.id}/refund/",
            {"amount": "500.00", "reason": "Partial service cancellation"},
            format="json",
        )
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/approve_refund/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_REFUNDED)
        self.assertEqual(self.payment.refund_status, "approved")
        self.assertEqual(self.payment.refund_approved_by, self.accountant)

    def test_reject_refund(self):
        self._auth(self.accountant)
        self.client.post(
            f"/api/billing/payments/{self.payment.id}/refund/",
            {"amount": "500.00", "reason": "Test"},
            format="json",
        )
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/reject_refund/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.refund_status, "rejected")
        self.assertEqual(self.payment.status, "completed")

    def test_refund_reverses_insurance_fields(self):
        ins_payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("1000.00"),
            method="insurance", status="completed",
            insurance_provider="Jubilee", insurance_amount=Decimal("800.00"),
            patient_copay=Decimal("200.00"),
        )
        self.invoice.insurance_covered_amount = Decimal("800.00")
        self.invoice.patient_copay_amount = Decimal("200.00")
        self.invoice.save(update_fields=["insurance_covered_amount", "patient_copay_amount"])

        self._auth(self.accountant)
        self.client.post(
            f"/api/billing/payments/{ins_payment.id}/refund/",
            {"amount": "1000.00", "reason": "Claim denied"},
            format="json",
        )
        self.client.post(
            f"/api/billing/payments/{ins_payment.id}/approve_refund/",
            format="json",
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.insurance_covered_amount, Decimal("0.00"))
        self.assertEqual(self.invoice.patient_copay_amount, Decimal("0.00"))

    def test_cannot_refund_non_completed_payment(self):
        self.payment.status = "pending"
        self.payment.save(update_fields=["status"])
        self._auth(self.accountant)
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/refund/",
            {"amount": "500.00", "reason": "Test"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_approve_without_pending(self):
        self._auth(self.accountant)
        resp = self.client.post(
            f"/api/billing/payments/{self.payment.id}/approve_refund/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Issue 7: Insurance Claim Status Validation
# ---------------------------------------------------------------------------

class InsuranceClaimValidationTests(BillingBaseTestCase):
    """Insurance payments must verify linked claim is approved."""

    def setUp(self):
        super().setUp()
        from apps.insurance.models import InsuranceClaim, InsurancePolicy, InsuranceProvider

        self.ins_provider = InsuranceProvider.objects.create(
            name="Jubilee", code="JUB",
        )
        self.ins_policy = InsurancePolicy.objects.create(
            patient=self.patient, provider=self.ins_provider,
            policy_number="POL-001", start_date=timezone.now().date(),
        )
        self.claim = InsuranceClaim.objects.create(
            policy=self.ins_policy, patient=self.patient,
            invoice=self.invoice, amount=Decimal("1000.00"),
            status=InsuranceClaim.STATUS_DRAFT,
        )
        self.invoice.insurance_claim = self.claim
        self.invoice.save(update_fields=["insurance_claim"])

    def test_insurance_payment_rejected_for_draft_claim(self):
        self._auth(self.accountant)
        resp = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1000.00",
            "method": "insurance",
            "insurance_provider": "Jubilee",
            "insurance_amount": "800.00",
            "patient_copay": "200.00",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_insurance_payment_allowed_for_approved_claim(self):
        from apps.insurance.models import InsuranceClaim
        self.claim.status = InsuranceClaim.STATUS_APPROVED
        self.claim.save(update_fields=["status"])

        self._auth(self.accountant)
        resp = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1000.00",
            "method": "insurance",
            "insurance_provider": "Jubilee",
            "insurance_amount": "800.00",
            "patient_copay": "200.00",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Issue 5: Idempotency
# ---------------------------------------------------------------------------

class IdempotencyTests(BillingBaseTestCase):
    """Duplicate idempotency keys must return the existing payment."""

    def test_duplicate_key_returns_existing(self):
        self._auth(self.accountant)
        resp1 = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "500.00",
            "method": "cash",
            "idempotency_key": "req-abc-123",
        }, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        id1 = resp1.data["id"]

        resp2 = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "500.00",
            "method": "cash",
            "idempotency_key": "req-abc-123",
        }, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data["id"], id1)
        self.assertEqual(Payment.objects.filter(idempotency_key="req-abc-123").count(), 1)

    def test_different_keys_create_separate_payments(self):
        self._auth(self.accountant)
        resp1 = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "300.00",
            "method": "cash",
            "idempotency_key": "req-001",
        }, format="json")
        resp2 = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "300.00",
            "method": "cash",
            "idempotency_key": "req-002",
        }, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp1.data["id"], resp2.data["id"])


# ---------------------------------------------------------------------------
# Issue 6: Credit / Overpayment
# ---------------------------------------------------------------------------

class CreditOverpaymentTests(BillingBaseTestCase):
    """Overpayment creates credit; payments consider available credit."""

    def test_overpayment_creates_negative_balance(self):
        self._auth(self.accountant)
        resp = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1200.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.balance, Decimal("-200.00"))

    def test_patient_credit_calculated_correctly(self):
        self._auth(self.accountant)
        self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1200.00",
            "method": "cash",
        }, format="json")
        credit = Invoice.patient_credit(self.patient)
        self.assertEqual(credit, Decimal("200.00"))

    def test_credit_applied_when_paying_second_invoice(self):
        self._auth(self.accountant)
        self.client.post("/api/billing/payments/", {
            "invoice": self.invoice.id,
            "amount": "1200.00",
            "method": "cash",
        }, format="json")

        resp = self.client.post("/api/billing/payments/", {
            "invoice": self.invoice2.id,
            "amount": "1200.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.invoice2.refresh_from_db()
        self.assertEqual(self.invoice2.balance, Decimal("-200.00"))

    def test_credit_visible_on_invoice_serializer(self):
        patient3 = Patient.objects.create(
            first_name="Alice", last_name="Jones",
            date_of_birth=timezone.now().date().replace(year=1992),
            gender="female", phone="0733000000",
        )
        inv_a = Invoice.objects.create(patient=patient3, issued_by=self.accountant)
        InvoiceItem.objects.create(invoice=inv_a, description="X", quantity=1, unit_price=Decimal("500.00"))
        inv_a.recalculate()

        inv_b = Invoice.objects.create(patient=patient3, issued_by=self.accountant)
        InvoiceItem.objects.create(invoice=inv_b, description="Y", quantity=1, unit_price=Decimal("300.00"))
        inv_b.recalculate()

        self._auth(self.accountant)
        self.client.post("/api/billing/payments/", {
            "invoice": inv_a.id, "amount": "700.00", "method": "cash",
        }, format="json")

        resp = self.client.get(f"/api/billing/{inv_b.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(resp.data["patient_credit"]), Decimal("200.00"))


# ---------------------------------------------------------------------------
# Issue 9: PDF Generation
# ---------------------------------------------------------------------------

class InvoicePDFTests(BillingBaseTestCase):
    """Invoice and receipt PDF generation."""

    def test_invoice_pdf_endpoint(self):
        self._auth(self.accountant)
        resp = self.client.get(f"/api/billing/{self.invoice.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn(self.invoice.invoice_number, resp["Content-Disposition"])

    def test_receipt_pdf_endpoint(self):
        payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("500.00"),
            method="cash", status="completed",
        )
        self._auth(self.accountant)
        resp = self.client.get(f"/api/billing/payments/{payment.id}/receipt-pdf/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn(payment.receipt_number, resp["Content-Disposition"])

    def test_patient_can_view_own_invoice_pdf(self):
        self._auth(self.patient_user)
        resp = self.client.get(f"/api/billing/{self.invoice.id}/pdf/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_patient_cannot_view_other_invoice_pdf(self):
        self._auth(self.patient_user)
        resp = self.client.get(f"/api/billing/{self.invoice2.id}/pdf/")
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])


# ---------------------------------------------------------------------------
# Gateway Reconciliation
# ---------------------------------------------------------------------------

class GatewayReconciliationTests(BillingBaseTestCase):
    """PaymentGatewayTransaction reconciliation workflow."""

    def test_create_gateway_transaction(self):
        self._auth(self.accountant)
        resp = self.client.post("/api/billing/gateway-transactions/", {
            "provider": "mpesa",
            "provider_reference": "QKJ4X7YZ9P",
            "provider_amount": "1000.00",
            "provider_timestamp": timezone.now().isoformat(),
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["reconciliation_status"], "unmatched")

    def test_reconcile_match(self):
        self._auth(self.accountant)
        payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("1000.00"),
            method="mpesa", status="completed",
        )
        resp = self.client.post("/api/billing/gateway-transactions/", {
            "provider": "mpesa",
            "provider_reference": "QKJ4X7YZ9P",
            "provider_amount": "1000.00",
        }, format="json")
        tx_id = resp.data["id"]

        resp = self.client.post(
            f"/api/billing/gateway-transactions/{tx_id}/reconcile/",
            {"payment": payment.id}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["reconciliation_status"], "matched")

    def test_reconcile_amount_mismatch(self):
        self._auth(self.accountant)
        payment = Payment.objects.create(
            invoice=self.invoice, amount=Decimal("800.00"),
            method="mpesa", status="completed",
        )
        resp = self.client.post("/api/billing/gateway-transactions/", {
            "provider": "mpesa",
            "provider_reference": "ABC123",
            "provider_amount": "1000.00",
        }, format="json")
        tx_id = resp.data["id"]

        resp = self.client.post(
            f"/api/billing/gateway-transactions/{tx_id}/reconcile/",
            {"payment": payment.id}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reconcile_dispute(self):
        self._auth(self.accountant)
        resp = self.client.post("/api/billing/gateway-transactions/", {
            "provider": "mpesa",
            "provider_reference": "UNKNOWN999",
            "provider_amount": "500.00",
        }, format="json")
        tx_id = resp.data["id"]

        resp = self.client.post(
            f"/api/billing/gateway-transactions/{tx_id}/reconcile/",
            {"notes": "No matching payment found"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["reconciliation_status"], "disputed")
