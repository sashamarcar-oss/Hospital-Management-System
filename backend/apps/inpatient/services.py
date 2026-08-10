import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_discharge_summary_pdf(discharge) -> io.BytesIO:
    """Generate a professional discharge summary PDF."""
    admission = discharge.admission
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Discharge Summary - {discharge.patient.full_name}")
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("HOSPITAL DISCHARGE SUMMARY", styles["Title"]))
    elements.append(Spacer(1, 12))

    info = [
        ["Patient", discharge.patient.full_name],
        ["Medical Record Number", discharge.patient.patient_number],
        ["Date of Birth / Age", f"{discharge.patient.date_of_birth} ({discharge.patient.age} yrs)"],
        ["Gender", discharge.patient.get_gender_display()],
        ["Admitted", str(admission.admission_date)],
        ["Discharged", str(discharge.discharge_date)],
        ["Ward", admission.ward.name if admission.ward else "-"],
        ["Attending Doctor", discharge.admission.doctor.get_full_name() if admission.doctor else "-"],
    ]
    info_table = Table(info, colWidths=[180, 340])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#0d9488")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    sections = [
        ("DIAGNOSIS SUMMARY", discharge.diagnosis_summary or "-"),
        ("TREATMENT SUMMARY", discharge.treatment_summary or "-"),
        ("MEDICATION ON DISCHARGE", discharge.medication or "-"),
        ("OUTSTANDING BILLS", discharge.outstanding_bills or "-"),
        ("FOLLOW-UP INSTRUCTIONS", discharge.follow_up_instructions or "-"),
        ("DOCTOR'S NOTES", discharge.doctor_notes or "-"),
    ]
    for title, body in sections:
        elements.append(Paragraph(title, styles["Heading3"]))
        elements.append(Paragraph(body.replace("\n", "<br/>"), styles["BodyText"]))
        elements.append(Spacer(1, 8))

    if discharge.follow_up_date:
        elements.append(Paragraph(
            f"Follow-up Appointment: {discharge.follow_up_date}", styles["BodyText"]
        ))

    elements.append(Spacer(1, 24))
    signature = Table([["_______________________", "_______________________"],
                       ["Doctor's Signature", "Hospital Stamp"]], colWidths=[260, 260])
    elements.append(signature)

    doc.build(elements)
    buffer.seek(0)
    return buffer
