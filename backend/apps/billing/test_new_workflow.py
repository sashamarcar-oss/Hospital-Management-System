"""Tests for the new invoice and payment workflow requirements.

Covers:
- Invoice creation without manual amount
- Invoice totals calculated from items
- Payment validation (0-total, overpayment)
- Multiple partial payments
- Proper decimal precision
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role
from apps.billing.models import Invoice, InvoiceItem, Payment
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


class InvoiceCreationWorkflowTests(APITestCase):
    """Test the new invoice creation workflow without amount field."""

    def setUp(self):
        self.user = create_user(
            "accountant", "accountant",
            permissions=["billing.view", "billing.update", "billing.create", "payments.receive_payment"],
        )
        self.patient = Patient.objects.create(
            first_name="Jane", last_name="Doe",
            date_of_birth="1990-01-01", gender="female", phone="0712000000",
        )
        self.client.force_authenticate(user=self.user)

    def test_invoice_creation_rejects_amount_field(self):
        """Attempting to set amount during invoice creation should fail."""
        resp = self.client.post("/api/billing/", {
            "patient": self.patient.id,
            "amount": "5000.00",  # This should be rejected
            "tax_rate": "16",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # The error might be nested in 'errors' or at top level depending on response format
        error_data = resp.data.get("errors", resp.data)
        self.assertIn("amount", error_data)

    def test_invoice_creation_without_amount_succeeds(self):
        """Invoice creation without amount field should succeed."""
        resp = self.client.post("/api/billing/", {
            "patient": self.patient.id,
            "tax_rate": "16",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["total"], "0.00")
        self.assertEqual(resp.data["status"], "unpaid")

    def test_invoice_total_zero_until_items_added(self):
        """Invoice should have zero total until items are added."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        self.assertEqual(invoice.total, Decimal("0.00"))
        self.assertEqual(invoice.balance, Decimal("0.00"))

    def test_adding_item_updates_invoice_total(self):
        """Adding an item should update invoice total automatically."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        self.assertEqual(invoice.total, Decimal("0.00"))

        item = InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.subtotal, Decimal("1000.00"))
        self.assertEqual(invoice.total, Decimal("1000.00"))
        self.assertEqual(invoice.balance, Decimal("1000.00"))

    def test_multiple_items_calculate_correctly(self):
        """Multiple items should sum correctly."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Consultation", quantity=1, unit_price=Decimal("1000.00"),
        )
        InvoiceItem.objects.create(
            invoice=invoice, description="Lab Test", quantity=2, unit_price=Decimal("500.00"),
        )
        InvoiceItem.objects.create(
            invoice=invoice, description="Medicine", quantity=1, unit_price=Decimal("200.00"),
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.subtotal, Decimal("2200.00"))
        self.assertEqual(invoice.total, Decimal("2200.00"))

    def test_tax_calculated_correctly_from_items(self):
        """Tax should be calculated from subtotal."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user, tax_rate=Decimal("16"))
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("1000.00"),
        )
        invoice.refresh_from_db()
        # 1000 * 0.16 = 160
        self.assertEqual(invoice.tax, Decimal("160.00"))
        # 1000 + 160 = 1160
        self.assertEqual(invoice.total, Decimal("1160.00"))

    def test_discount_applied_correctly(self):
        """Discount should reduce the total."""
        invoice = Invoice.objects.create(
            patient=self.patient, issued_by=self.user, discount=Decimal("100.00"),
        )
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("1000.00"),
        )
        invoice.refresh_from_db()
        # 1000 - 100 = 900
        self.assertEqual(invoice.total, Decimal("900.00"))


class PaymentValidationTests(APITestCase):
    """Test payment validation rules."""

    def setUp(self):
        self.user = create_user(
            "accountant", "accountant",
            permissions=["billing.view", "billing.update", "payments.receive_payment"],
        )
        self.patient = Patient.objects.create(
            first_name="John", last_name="Smith",
            date_of_birth="1985-01-01", gender="male", phone="0722000000",
        )
        self.client.force_authenticate(user=self.user)

    def test_payment_rejected_on_zero_total_invoice(self):
        """Payment should be rejected on invoice with zero total (no items)."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        self.assertEqual(invoice.total, Decimal("0.00"))

        resp = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "100.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        error_data = resp.data.get("errors", resp.data)
        self.assertIn("invoice", error_data)

    def test_payment_rejected_on_overpayment(self):
        """Overpayments are allowed and create customer credit."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("5000.00"),
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.balance, Decimal("5000.00"))

        # Overpayment should be accepted and create credit
        resp = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "6000.00",  # Exceeds balance
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        # Balance goes negative (customer credit)
        self.assertEqual(invoice.balance, Decimal("-1000.00"))

    def test_payment_accepted_within_balance(self):
        """Payment within balance should be accepted."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("5000.00"),
        )
        invoice.refresh_from_db()

        resp = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "3000.00",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("3000.00"))
        self.assertEqual(invoice.balance, Decimal("2000.00"))

    def test_decimal_precision_maintained_in_payment(self):
        """Payment amounts should maintain decimal precision."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=3, unit_price=Decimal("333.33"),
        )
        invoice.refresh_from_db()
        # 3 * 333.33 = 999.99
        self.assertEqual(invoice.total, Decimal("999.99"))

        resp = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id,
            "amount": "333.33",
            "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("333.33"))
        self.assertEqual(invoice.balance, Decimal("666.66"))


class MultiplePaymentWorkflowTests(APITestCase):
    """Test workflow with multiple partial payments."""

    def setUp(self):
        self.user = create_user(
            "accountant", "accountant",
            permissions=["billing.view", "billing.update", "payments.receive_payment"],
        )
        self.patient = Patient.objects.create(
            first_name="Alice", last_name="Johnson",
            date_of_birth="1992-01-01", gender="female", phone="0711000000",
        )
        self.client.force_authenticate(user=self.user)

    def test_multiple_partial_payments_workflow(self):
        """Test: Invoice 10,000 → Pay 3,000 → Pay 4,000 → Pay 3,000 → PAID."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("10000.00"),
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.total, Decimal("10000.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_UNPAID)

        # First payment: 3000
        resp1 = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id, "amount": "3000.00", "method": "cash",
        }, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("3000.00"))
        self.assertEqual(invoice.balance, Decimal("7000.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_PARTIALLY_PAID)

        # Second payment: 4000
        resp2 = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id, "amount": "4000.00", "method": "cash",
        }, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("7000.00"))
        self.assertEqual(invoice.balance, Decimal("3000.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_PARTIALLY_PAID)

        # Third payment: 3000 (final)
        resp3 = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id, "amount": "3000.00", "method": "cash",
        }, format="json")
        self.assertEqual(resp3.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("10000.00"))
        self.assertEqual(invoice.balance, Decimal("0.00"))
        self.assertEqual(invoice.status, Invoice.STATUS_PAID)

    def test_overpayment_creates_customer_credit(self):
        """Overpayment creates negative balance (customer credit)."""
        invoice = Invoice.objects.create(patient=self.patient, issued_by=self.user)
        InvoiceItem.objects.create(
            invoice=invoice, description="Service", quantity=1, unit_price=Decimal("5000.00"),
        )
        invoice.refresh_from_db()

        # Overpay - should succeed and create credit
        resp = self.client.post("/api/billing/payments/", {
            "invoice": invoice.id, "amount": "5001.00", "method": "cash",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Balance should be negative (customer credit)
        invoice.refresh_from_db()
        self.assertEqual(invoice.balance, Decimal("-1.00"))
