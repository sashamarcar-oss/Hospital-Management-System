import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BRAND_COLOR = colors.HexColor("#0d9488")


def _header_styles():
    styles = getSampleStyleSheet()
    return styles


def build_invoice_pdf(invoice) -> io.BytesIO:
    """Generate a professional invoice PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Invoice {invoice.invoice_number}")
    styles = _header_styles()
    elements = []

    elements.append(Paragraph("INVOICE", styles["Title"]))
    elements.append(Spacer(1, 8))

    patient = invoice.patient
    info = [
        ["Invoice Number", invoice.invoice_number],
        ["Date", str(invoice.issued_at.date())],
        ["Due Date", str(invoice.due_date) if invoice.due_date else "-"],
        ["Status", invoice.get_status_display()],
        ["", ""],
        ["Patient", patient.full_name],
        ["Patient ID", patient.patient_number],
        ["Phone", patient.phone or "-"],
        ["Email", patient.email or "-"],
    ]
    info_table = Table(info, colWidths=[140, 360])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    header_row = ["Description", "Qty", "Unit Price", "Line Total"]
    data_rows = []
    for item in invoice.items.all():
        data_rows.append([
            item.description,
            str(item.quantity),
            f"{item.unit_price:,.2f}",
            f"{item.line_total:,.2f}",
        ])
    data_rows.append(["", "", "Subtotal", f"{invoice.subtotal:,.2f}"])
    if invoice.discount:
        data_rows.append(["", "", "Discount", f"-{invoice.discount:,.2f}"])
    if invoice.tax:
        data_rows.append(["", "", "Tax", f"{invoice.tax:,.2f}"])
    data_rows.append(["", "", "TOTAL", f"{invoice.total:,.2f}"])
    data_rows.append(["", "", "Amount Paid", f"{invoice.amount_paid:,.2f}"])
    data_rows.append(["", "", "Balance", f"{invoice.balance:,.2f}"])

    items_table = Table([header_row] + data_rows, colWidths=[240, 60, 100, 100])
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (-2, -3), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 12))

    if invoice.insurance_covered_amount:
        elements.append(Paragraph(
            f"Insurance Covered: {invoice.insurance_covered_amount:,.2f}", styles["BodyText"]
        ))
    if invoice.patient_copay_amount:
        elements.append(Paragraph(
            f"Patient Co-pay: {invoice.patient_copay_amount:,.2f}", styles["BodyText"]
        ))

    credit = invoice.patient_credit(invoice.patient, exclude_pk=invoice.pk)
    if credit > 0:
        elements.append(Paragraph(
            f"Available Patient Credit: {credit:,.2f}", styles["BodyText"]
        ))

    if invoice.notes:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Notes", styles["Heading3"]))
        elements.append(Paragraph(invoice.notes, styles["BodyText"]))

    elements.append(Spacer(1, 24))
    footer = Table(
        [["_______________________", "_______________________"],
         ["Patient Signature", "Authorized Signature"]],
        colWidths=[250, 250],
    )
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_receipt_pdf(payment) -> io.BytesIO:
    """Generate a payment receipt PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Receipt {payment.receipt_number}")
    styles = _header_styles()
    elements = []

    elements.append(Paragraph("MIMOSA HOSPITAL", styles["Title"]))
    elements.append(Paragraph("PAYMENT RECEIPT", styles["Heading2"]))
    elements.append(Spacer(1, 8))

    invoice = payment.invoice
    patient = invoice.patient

    info = [
        ["Receipt Number", payment.receipt_number],
        ["Payment ID", getattr(payment, 'payment_number', payment.receipt_number)],
        ["Date", str(payment.paid_at.date())],
        ["Invoice", invoice.invoice_number],
        ["", ""],
        ["Patient", patient.full_name],
        ["Patient ID", patient.patient_number],
        ["Phone", patient.phone or "-"],
        ["", ""],
        ["Amount Paid", f"{payment.amount:,.2f}"],
        ["Payment Method", payment.get_method_display()],
    ]
    if payment.reference:
        info.append(["Reference", payment.reference])
    if payment.method in ("mpesa", "mobile_money") and payment.mpesa_transaction_code:
        info.append(["M-Pesa Code", payment.mpesa_transaction_code])
    if payment.method == "insurance":
        info.append(["Insurance Provider", payment.insurance_provider])
        info.append(["Policy Number", payment.policy_number])

    info_table = Table(info, colWidths=[160, 340])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    summary = [
        ["Invoice Total", f"{invoice.total:,.2f}"],
        ["Previously Paid", f"{invoice.amount_paid - payment.amount:,.2f}"],
        ["This Payment", f"{payment.amount:,.2f}"],
        ["Remaining Balance", f"{invoice.balance:,.2f}"],
    ]
    summary_table = Table(summary, colWidths=[200, 120])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(Paragraph("Invoice Summary", styles["Heading3"]))
    elements.append(summary_table)

    if payment.notes:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Notes: {payment.notes}", styles["BodyText"]))

    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Thank you for your payment.", styles["BodyText"]))
    elements.append(Spacer(1, 16))
    footer = Table(
        [["_______________________", "_______________________"],
         ["Cashier Signature", "Hospital Stamp"]],
        colWidths=[250, 250],
    )
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer
