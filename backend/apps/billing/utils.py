from apps.billing.models import Invoice, InvoiceItem


def get_or_create_open_invoice(patient, created_by=None):
    """Return the patient's open (unpaid/partial) invoice or create a new one."""
    invoice = (
        Invoice.objects.filter(
            patient=patient, status__in=[Invoice.STATUS_UNPAID, Invoice.STATUS_PARTIALLY_PAID, Invoice.STATUS_OVERDUE]
        )
        .order_by("issued_at")
        .first()
    )
    if not invoice:
        invoice = Invoice.objects.create(patient=patient, issued_by=created_by)
    return invoice


def add_charge(patient, description, quantity, unit_price, created_by=None, **refs):
    """Add a charge line to the patient's open invoice and return the invoice."""
    invoice = get_or_create_open_invoice(patient, created_by)
    InvoiceItem.objects.create(
        invoice=invoice,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        created_by=created_by,
        **refs,
    )
    invoice.recalculate()
    return invoice
