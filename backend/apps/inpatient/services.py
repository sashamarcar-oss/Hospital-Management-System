import io

from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.models import AuditLog
from apps.core.services import audit_log, notify
from apps.inpatient.models import (
    Admission,
    Bed,
    BedAssignment,
    ICUThreshold,
    NurseAssignment,
)


# ============================================================================
# BED MANAGEMENT SERVICES
# ============================================================================


class BedManagementError(Exception):
    """Raised when a bed operation violates an invariant."""


def _validate_bed_assignable(admission, bed):
    if admission.status == Admission.STATUS_DISCHARGED:
        raise BedManagementError("A discharged patient cannot be assigned a bed.")
    if admission.status == Admission.STATUS_TRANSFERRED and not admission.bed_id:
        raise BedManagementError("This admission has been transferred out and is no longer on a bed.")
    if bed.status in (Bed.STATUS_MAINTENANCE, Bed.STATUS_OUT_OF_SERVICE):
        raise BedManagementError("The bed is not available for assignment (maintenance or out of service).")
    if bed.status == Bed.STATUS_CLEANING:
        raise BedManagementError("The bed is under cleaning and cannot be assigned yet.")

    active = bed.assignment_history.filter(released_at__isnull=True).select_related("admission").first()
    if active and active.admission_id != admission.pk:
        raise BedManagementError("This bed is already occupied or reserved.")


@transaction.atomic
def assign_patient_to_bed(
    admission,
    bed,
    user,
    expected_discharge_date=None,
    notes="",
    reason="Admission",
    notify_staff=True,
):
    """Assign an admitted patient to a bed, creating a bed-assignment record."""
    admission = Admission.objects.select_for_update().get(pk=admission.pk)
    bed = Bed.objects.select_for_update().get(pk=bed.pk)
    _validate_bed_assignable(admission, bed)

    active = bed.assignment_history.filter(released_at__isnull=True).select_related("admission").first()
    fulfilling_reservation = (
        active is not None
        and active.admission_id == admission.pk
        and bed.status == Bed.STATUS_RESERVED
    )
    if not fulfilling_reservation and admission.bed_assignments.filter(
        released_at__isnull=True
    ).exists():
        raise BedManagementError(
            "This admission already has an active bed assignment. Transfer or release it first."
        )

    if bed.status == Bed.STATUS_RESERVED:
        reserved = bed.assignment_history.filter(released_at__isnull=True).select_related("admission").first()
        if reserved and reserved.admission_id == admission.pk:
            reserved.release(user=user, reason="Reservation fulfilled")

    bed.status = Bed.STATUS_OCCUPIED
    bed.save(update_fields=["status", "updated_at"])

    assignment = BedAssignment.objects.create(
        admission=admission,
        bed=bed,
        ward=bed.room.ward,
        room=bed.room,
        assigned_at=timezone.now(),
        expected_discharge_date=expected_discharge_date,
        assigned_by=user,
        notes=notes,
        created_by=user,
    )
    admission.ward = bed.room.ward
    admission.room = bed.room
    admission.bed = bed
    admission.expected_discharge_date = expected_discharge_date or admission.expected_discharge_date
    admission.save()

    audit_log(
        user,
        AuditLog.ACTION_CREATE,
        "inpatient.bedassignment",
        record=f"{admission.patient} -> {bed}",
        object_id=assignment.id,
        new_value={
            "admission": admission.id,
            "bed": bed.id,
            "reason": reason,
            "expected_discharge_date": str(expected_discharge_date) if expected_discharge_date else None,
        },
        description=f"Assigned patient to bed {bed.bed_number}",
    )

    if notify_staff:
        _notify_bed_assignees(admission, f"assigned to bed {bed.bed_number} ({bed.room.ward.name})", "bed_assignment")
    return assignment


@transaction.atomic
def transfer_patient_bed(admission, new_bed, user, reason="Transfer", notes=""):
    """Atomically release the old bed and assign the patient to a new one."""
    admission = Admission.objects.select_for_update().get(pk=admission.pk)
    new_bed = Bed.objects.select_for_update().get(pk=new_bed.pk)

    if admission.status == Admission.STATUS_DISCHARGED:
        raise BedManagementError("A discharged patient cannot be transferred.")

    old_assignment = admission.bed_assignments.filter(released_at__isnull=True).select_for_update().first()
    if not old_assignment or not admission.bed_id:
        raise BedManagementError("This admission has no active bed assignment to transfer from.")

    if new_bed.id == admission.bed_id:
        raise BedManagementError("The patient is already assigned to this bed.")

    _validate_bed_assignable(admission, new_bed)

    old_bed = admission.bed
    old_assignment.release(user=user, reason=f"Transfer to {new_bed.bed_number}")
    Bed.objects.filter(pk=old_bed.id).update(status=Bed.STATUS_AVAILABLE)

    new_bed.status = Bed.STATUS_OCCUPIED
    new_bed.save(update_fields=["status", "updated_at"])

    new_assignment = BedAssignment.objects.create(
        admission=admission,
        bed=new_bed,
        ward=new_bed.room.ward,
        room=new_bed.room,
        assigned_at=timezone.now(),
        assigned_by=user,
        notes=notes,
        created_by=user,
    )
    admission.ward = new_bed.room.ward
    admission.room = new_bed.room
    admission.bed = new_bed
    admission.save()

    audit_log(
        user,
        AuditLog.ACTION_UPDATE,
        "inpatient.bedtransfer",
        record=str(admission.patient),
        object_id=new_assignment.id,
        previous_value={"bed": old_bed.bed_number, "ward": old_bed.room.ward.name},
        new_value={"bed": new_bed.bed_number, "ward": new_bed.room.ward.name},
        description=f"Transferred patient from bed {old_bed.bed_number} to bed {new_bed.bed_number}",
    )

    _notify_bed_assignees(
        admission,
        f"transferred from {old_bed.bed_number} to {new_bed.bed_number}",
        "transfer",
    )
    return new_assignment


@transaction.atomic
def release_bed(admission, user, reason="Discharge", set_cleaning=False):
    """Release the active bed assignment and free the bed."""
    admission = Admission.objects.select_for_update().get(pk=admission.pk)
    assignment = admission.bed_assignments.filter(released_at__isnull=True).select_for_update().first()
    if not assignment:
        raise BedManagementError("This admission has no active bed assignment.")

    bed = assignment.bed
    assignment.release(user=user, reason=reason)
    new_status = Bed.STATUS_CLEANING if set_cleaning else Bed.STATUS_AVAILABLE
    Bed.objects.filter(pk=bed.pk).update(
        status=new_status,
        last_cleaned_at=timezone.now() if set_cleaning else None,
    )
    admission.bed = None
    admission.room = None
    admission.ward = None
    admission.save(update_fields=["bed", "room", "ward", "updated_at"])

    audit_log(
        user,
        AuditLog.ACTION_UPDATE,
        "inpatient.bedrelease",
        record=str(admission.patient),
        object_id=assignment.id,
        previous_value={"bed": bed.bed_number},
        new_value={"released": True, "reason": reason},
        description=f"Released bed {bed.bed_number} ({reason})",
    )
    return assignment


@transaction.atomic
def reserve_bed(bed, user, admission=None, notes="", expected_discharge_date=None):
    """Reserve an available bed, optionally for a specific admission."""
    bed = Bed.objects.select_for_update().get(pk=bed.pk)
    if bed.status != Bed.STATUS_AVAILABLE:
        raise BedManagementError("Only an available bed can be reserved.")
    bed.status = Bed.STATUS_RESERVED
    bed.save(update_fields=["status", "updated_at"])

    assignment = None
    if admission:
        assignment = BedAssignment.objects.create(
            admission=admission,
            bed=bed,
            ward=bed.room.ward,
            room=bed.room,
            expected_discharge_date=expected_discharge_date,
            assigned_by=user,
            notes=notes,
            created_by=user,
        )
    audit_log(
        user,
        AuditLog.ACTION_UPDATE,
        "inpatient.bed",
        record=str(bed),
        object_id=bed.id,
        description=f"Bed {bed.bed_number} reserved",
    )
    return assignment


@transaction.atomic
def mark_bed_status(bed, user, new_status, reason=""):
    """Change bed operational status with guards (cleaning / maintenance / etc.)."""
    bed = Bed.objects.select_for_update().get(pk=bed.pk)
    valid = dict(Bed.STATUS_CHOICES)
    if new_status not in valid:
        raise BedManagementError("Invalid bed status.")

    if new_status == Bed.STATUS_OCCUPIED:
        raise BedManagementError("Mark occupied by assigning a patient through the bed assignment workflow.")
    if bed.status == Bed.STATUS_OCCUPIED and new_status != bed.status:
        raise BedManagementError("Release the bed assignment before changing the bed status.")

    bed.status = new_status
    if new_status == Bed.STATUS_CLEANING:
        bed.last_cleaned_at = timezone.now()
    elif new_status == Bed.STATUS_AVAILABLE:
        bed.last_cleaned_at = timezone.now()
    bed.save(update_fields=["status", "last_cleaned_at", "updated_at"])

    audit_log(
        user,
        AuditLog.ACTION_UPDATE,
        "inpatient.bed",
        record=str(bed),
        object_id=bed.id,
        previous_value={"status": ""},
        new_value={"status": new_status},
        description=f"Bed {bed.bed_number} status set to {valid[new_status]}{' - ' + reason if reason else ''}",
    )
    return bed


@transaction.atomic
def assign_nurse_to_admission(admission, nurse, user, role=NurseAssignment.ROLE_PRIMARY, notes=""):
    admission = Admission.objects.select_for_update().get(pk=admission.pk)
    assignment, _ = NurseAssignment.objects.get_or_create(
        admission=admission,
        nurse=nurse,
        unassigned_at__isnull=True,
        defaults={"assigned_by": user, "role": role, "notes": notes, "created_by": user},
    )
    if role == NurseAssignment.ROLE_PRIMARY:
        admission.assigned_nurse = nurse
        admission.save(update_fields=["assigned_nurse", "updated_at"])
    audit_log(
        user,
        AuditLog.ACTION_CREATE,
        "inpatient.nurseassignment",
        record=f"{nurse} -> {admission}",
        object_id=assignment.id,
        description=f"Nurse {nurse.get_full_name()} assigned to {admission.patient}",
    )
    return assignment


def _notify_bed_assignees(admission, action_text, notification_type):
    """Notify the attending doctor and assigned nurse about bed activity."""
    recipients = set()
    if admission.assigned_nurse_id:
        recipients.add(admission.assigned_nurse_id)
    if admission.doctor_id:
        recipients.add(admission.doctor_id)

    title = {
        "bed_assignment": "Bed assigned",
        "transfer": "Patient transferred",
    }.get(notification_type, "Inpatient update")

    for user_id in recipients:
        try:
            from apps.accounts.models import User

            user = User.objects.get(pk=user_id)
            notify(
                user,
                title,
                f"{admission.patient.full_name} {action_text}.",
                notification_type=notification_type,
                link="/inpatient/bed-board",
                related_module="inpatient",
                related_object_id=admission.id,
            )
        except User.DoesNotExist:
            continue


# ============================================================================
# ICU SERVICES
# ============================================================================


def evaluate_icu_record_alerts(record):
    """Evaluate an ICU record against configured clinical thresholds.

    Returns a list of alert dicts. Alerts are decision-support flags only and
    never constitute a diagnosis.
    """
    thresholds = {t.parameter: t for t in ICUThreshold.objects.filter(is_active=True)}
    candidates = {
        "heart_rate": record.heart_rate,
        "temperature": float(record.temperature) if record.temperature is not None else None,
        "bp_systolic": record.blood_pressure_systolic,
        "bp_diastolic": record.blood_pressure_diastolic,
        "map": record.map_arterial,
        "respiratory_rate": record.respiratory_rate,
        "spo2": record.effective_spo2,
        "blood_glucose": float(record.blood_glucose) if record.blood_glucose is not None else None,
        "gcs_total": record.gcs_total,
        "pain_score": record.pain_score,
    }
    alerts = []
    for parameter, value in candidates.items():
        threshold = thresholds.get(parameter)
        if not threshold:
            continue
        for alert in threshold.evaluate(value):
            alerts.append({
                "parameter": alert["parameter"],
                "parameter_name": threshold.get_parameter_display(),
                "value": value,
                "unit": threshold.unit,
                "severity": alert["severity"],
                "direction": alert["direction"],
            })
    return alerts


# ============================================================================
# TIMELINE
# ============================================================================


def _person_name(user):
    if user is None:
        return "System"
    return user.get_full_name() or user.username


def build_patient_timeline(admission):
    """Build a chronological inpatient journey for an admission."""
    patient = admission.patient
    events = []

    events.append({
        "timestamp": admission.admission_date,
        "type": "admission",
        "title": "Patient admitted",
        "description": admission.admission_reason or admission.diagnosis or "",
        "actor": _person_name(admission.created_by),
    })

    for assignment in admission.bed_assignments.select_related("bed", "bed__room__ward", "assigned_by"):
        events.append({
            "timestamp": assignment.assigned_at,
            "type": "bed_assignment",
            "title": f"Assigned to Bed {assignment.bed.bed_number}",
            "description": f"{assignment.bed.room.ward.name} · {assignment.bed.room.room_number}",
            "actor": _person_name(assignment.assigned_by),
        })
        if assignment.released_at:
            events.append({
                "timestamp": assignment.released_at,
                "type": "bed_release",
                "title": f"Released from Bed {assignment.bed.bed_number}",
                "description": assignment.release_reason or "",
                "actor": _person_name(assignment.released_by),
            })

    for vital in patient.vital_signs.filter(admission=admission).select_related("recorded_by"):
        bp = ""
        if vital.blood_pressure_systolic:
            bp = f"{vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}"
        details = ", ".join(
            filter(None, [
                f"BP {bp}" if bp else "",
                f"HR {vital.pulse}" if vital.pulse else "",
                f"Temp {vital.temperature}°C" if vital.temperature else "",
                f"SpO2 {vital.oxygen_saturation}%" if vital.oxygen_saturation else "",
            ])
        )
        events.append({
            "timestamp": vital.recorded_at,
            "type": "vitals",
            "title": "Vital signs recorded",
            "description": details,
            "actor": _person_name(vital.recorded_by),
        })

    for note in admission.nursing_notes.select_related("nurse").filter(status__in=["submitted", "amended"]):
        events.append({
            "timestamp": note.recorded_at,
            "type": "nursing_note",
            "title": "Nursing shift note added",
            "description": (note.note or note.observations or note.handover_current_condition or "")[:200],
            "actor": _person_name(note.nurse),
        })

    for handover in admission.handovers.select_related("nurse"):
        events.append({
            "timestamp": handover.recorded_at,
            "type": "handover",
            "title": "Shift handover completed",
            "description": handover.current_condition or handover.observations or "",
            "actor": _person_name(handover.nurse),
        })

    for consultation in patient.consultations.select_related("doctor"):
        events.append({
            "timestamp": consultation.recorded_at,
            "type": "consultation",
            "title": "Doctor reviewed patient",
            "description": consultation.chief_complaint or consultation.clinical_notes or "",
            "actor": _person_name(consultation.doctor),
        })

    for prescription in patient.prescriptions.select_related("doctor"):
        events.append({
            "timestamp": prescription.created_at,
            "type": "medication",
            "title": "Medication prescribed",
            "description": prescription.notes or "",
            "actor": _person_name(prescription.doctor),
        })

    for lab in patient.lab_requests.select_related("doctor"):
        events.append({
            "timestamp": lab.requested_at,
            "type": "laboratory",
            "title": "Laboratory request made",
            "description": lab.get_status_display() + (f" · {lab.priority}" if lab.priority else ""),
            "actor": _person_name(lab.doctor),
        })
        if lab.completed_at:
            events.append({
                "timestamp": lab.completed_at,
                "type": "laboratory_result",
                "title": "Laboratory result received",
                "description": f"{lab.patient} test batch completed",
                "actor": _person_name(lab.created_by),
            })

    for imaging in patient.radiology_requests.select_related("doctor"):
        events.append({
            "timestamp": imaging.requested_at,
            "type": "radiology",
            "title": "Imaging requested",
            "description": f"{imaging.get_procedure_type_display()} · {imaging.body_part}",
            "actor": _person_name(imaging.doctor),
        })

    for fluid in admission.fluid_balances.select_related("nurse"):
        events.append({
            "timestamp": fluid.created_at,
            "type": "fluid_balance",
            "title": "Fluid balance updated",
            "description": f"Net {fluid.net_balance_ml or 0} ml for {fluid.balance_date} ({fluid.get_period_display()})",
            "actor": _person_name(fluid.nurse),
        })

    for record in admission.icu_records.select_related("nurse"):
        events.append({
            "timestamp": record.recorded_at,
            "type": "icu",
            "title": "ICU observation recorded",
            "description": f"HR {record.heart_rate} · BP {record.blood_pressure} · SpO2 {record.effective_spo2}%",
            "actor": _person_name(record.nurse),
        })

    discharge = getattr(admission, "discharge", None)
    if discharge:
        events.append({
            "timestamp": discharge.discharge_date,
            "type": "discharge",
            "title": "Patient discharged",
            "description": discharge.discharge_type or "",
            "actor": _person_name(discharge.discharged_by),
        })

    events.sort(key=lambda e: e["timestamp"])
    return events


# ============================================================================
# DISCHARGE SUMMARY PDF (legacy helper)
# ============================================================================


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
