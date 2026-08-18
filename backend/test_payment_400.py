import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
django.setup()

from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Permission
from apps.billing.models import Invoice, InvoiceItem, Payment
from apps.patients.models import Patient
from django.utils import timezone

User = get_user_model()

@override_settings(ALLOWED_HOSTS=['*'])
class Payment400Test(APITestCase):
    def setUp(self):
        role, _ = Role.objects.get_or_create(code='accountant', defaults={'name': 'accountant'})
        for code in ['billing.view', 'billing.update', 'billing.create', 'payments.view', 'payments.receive_payment', 'payments.reverse']:
            perm, _ = Permission.objects.get_or_create(code=code, defaults={'name': code, 'module': code.split('.')[0]})
            role.permissions.add(perm)
        self.user = User.objects.create_user(username='test_pay3', password='test1234', role=role)
        self.client.force_authenticate(user=self.user)

    def test_payments_list(self):
        resp = self.client.get('/api/billing/payments/', {'page_size': '100', 'ordering': '-paid_at'})
        print(f'1. GET /payments/ -> {resp.status_code}')
        self.assertEqual(resp.status_code, 200)

    def test_payment_stats(self):
        resp = self.client.get('/api/billing/payments/stats/')
        print(f'2. GET /payments/stats/ -> {resp.status_code}')
        self.assertEqual(resp.status_code, 200)

    def test_payment_detail(self):
        resp = self.client.get('/api/billing/payments/1/')
        print(f'3. GET /payments/1/ -> {resp.status_code}')

    def test_payment_create_on_paid_invoice(self):
        resp = self.client.post('/api/billing/payments/',
            data={'invoice': 20, 'amount': 100, 'method': 'cash'},
            format='json')
        print(f'4. POST /payments/ (cash, inv=20 PAID) -> {resp.status_code}')
        print(f'   Body: {resp.content.decode()[:500]}')
        return resp.status_code

    def test_payment_create_on_unpaid_invoice(self):
        patient = Patient.objects.get(id=76)
        inv = Invoice.objects.create(patient=patient, issued_by=self.user, created_by=self.user, due_date=timezone.now().date())
        InvoiceItem.objects.create(invoice=inv, description='Consultation', quantity=1, unit_price=5000)
        inv.recalculate()
        inv.refresh_from_db()
        print(f'\n5a. Invoice {inv.invoice_number}: total={inv.total}, balance={inv.balance}, status={inv.status}')

        resp = self.client.post('/api/billing/payments/',
            data={'invoice': inv.id, 'amount': 2000, 'method': 'cash'},
            format='json')
        print(f'5b. POST /payments/ (cash, inv={inv.id}, 2000) -> {resp.status_code}')
        print(f'    Body: {resp.content.decode()[:500]}')
        return resp.status_code

    def test_invoice_list_for_patient(self):
        resp = self.client.get('/api/billing/', {'patient_id': 76, 'page_size': 50})
        print(f'\n6. GET /billing/?patient_id=76 -> {resp.status_code}')
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            print(f'   Found {len(results)} invoices')
            for inv in results:
                print(f'   {inv["invoice_number"]}: total={inv["total"]}, paid={inv["amount_paid"]}, balance={inv["balance"]}, status={inv["status"]}')
        else:
            print(f'   Body: {resp.content.decode()[:500]}')
        return resp.status_code


if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(Payment400Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
