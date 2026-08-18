from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.models import User
from apps.accounts.permissions import HasPermission
from apps.clinical.models import VitalSigns
from apps.core.models import AuditLog, Notification
from apps.core.services import audit_log, notify
from apps.inpatient.models import (
    Admission,
    Bed,
    BedAssignment,
    Discharge,
    FluidBalance,
    ICUMonitoringRecord,
    ICUMonitoringSheet,
    ICUThreshold,
    NurseAssignment,
    NursingHandover,
    NursingNote,
    Room,
    Ward,
)
from apps.inpatient.serializers import (
    AdmissionSerializer,
    BedAssignmentSerializer,
    BedSerializer,
    DischargeSerializer,
    FluidBalanceSerializer,
    ICUMonitoringRecordSerializer,
    ICUMonitoringSheetSerializer,
    ICUThresholdSerializer,
    NurseAssignmentSerializer,
    NursingHandoverSerializer,
    NursingNoteSerializer,
    RoomSerializer,
    TransferSerializer,
    WardSerializer,
)
from apps.inpatient.permissions import InpatientActionPermission
from apps.inpatient.services import (
    BedManagementError,
    assign_nurse_to_admission,
    assign_patient_to_bed,
    build_patient_timeline,
    mark_bed_status,
    release_bed,
    reserve_bed,
    transfer_patient_bed,
)


def require_permission(user, *codes):
    if not user.has_any_permission_code(codes):
        raise PermissionDenied("You do not have permission to perform this action.")


# ---------------------------------------------------------------------------
# Helpers for role-scoped querysets
# ---------------------------------------------------------------------------


def _patient_admissions(user):
    linked = getattr(user, "patient_account", None)
    return Admission.objects.filter(patient=linked) if linked else Admission.objects.none()


def _doctor_admissions(user):
    return Admission.objects.filter(doctor=user)


def _nurse_admissions(user):
    return Admission.objects.filter(
        Q(assigned_nurse=user)
        | Q(nurse_assignments__nurse=user, nurse_assignments__unassigned_at__isnull=True)
    ).distinct()


def _role_scoped_admissions(user):
    if user.in_roles("patient"):
        return _patient_admissions(user)
    if user.in_roles("doctor"):
        return _doctor_admissions(user)
    if user.in_roles("nurse", "icu_nurse"):
        return _nurse_admissions(user)
    return Admission.objects.all()


class WardViewSet(viewsets.ModelViewSet):
    queryset = Ward.objects.prefetch_related("rooms__beds").all()
    serializer_class = WardSerializer
    permission_classes = [HasPermission]
    code = "admissions.view"
    write_code = "admissions.update"
    search_fields = ["name", "code"]
    filterset_fields = ["ward_type", "is_active"]
    ordering_fields = ["name"]


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related("ward").all()
    serializer_class = RoomSerializer
    permission_classes = [HasPermission]
    code = "admissions.view"
    write_code = "admissions.update"
    filterset_fields = ["ward", "room_type"]


class BedViewSet(viewsets.ModelViewSet):
    queryset = Bed.objects.select_related("room__ward").all()
    serializer_class = BedSerializer
    permission_classes = [InpatientActionPermission]
    code = "inpatient.view"
    write_code = "inpatient.manage_beds"
    filterset_fields = ["status", "room", "room__ward"]

    def get_queryset(self):
        return super().get_queryset().filter(room__ward__is_active=True)

    @action(detail=False, methods=["get"])
    def board(self, request):
        """Visual bed-management board grouped by ward."""
        result = []
        for ward in Ward.objects.filter(is_active=True):
            beds = Bed.objects.filter(room__ward=ward).select_related("room")
            result.append({
                "ward": {"id": ward.id, "name": ward.name, "type": ward.ward_type},
                "beds": BedSerializer(beds, many=True).data,
            })
        return Response(result)

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        bed = self.get_object()
        require_permission(request.user, "inpatient.manage_beds", "admissions.update")
        new_status = request.data.get("status")
        if new_status == bed.status:
            return Response(BedSerializer(bed).data)
        try:
            bed = mark_bed_status(bed, request.user, new_status, request.data.get("reason", ""))
        except BedManagementError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BedSerializer(bed).data)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Assign a patient (via an admission) to this bed."""
        require_permission(request.user, "inpatient.assign_bed", "admissions.assign_bed")
        bed = Bed.objects.select_for_update().get(pk=self.get_object().pk)
        admission = Admission.objects.filter(pk=request.data.get("admission")).first()
        if not admission:
            return Response({"detail": "A valid admitted admission is required."}, status=400)
        try:
            assignment = assign_patient_to_bed(
                admission,
                bed,
                request.user,
                expected_discharge_date=request.data.get("expected_discharge_date") or None,
                notes=request.data.get("notes", ""),
                reason=request.data.get("reason", "Admission"),
            )
        except BedManagementError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BedAssignmentSerializer(assignment).data, status=201)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="reserve")
    def reserve(self, request, pk=None):
        require_permission(request.user, "inpatient.reserve_bed", "admissions.assign_bed")
        bed = Bed.objects.select_for_update().get(pk=self.get_object().pk)
        admission_id = request.data.get("admission")
        admission = Admission.objects.filter(pk=admission_id).first() if admission_id else None
        try:
            assignment = reserve_bed(
                bed,
                request.user,
                admission=admission,
                notes=request.data.get("notes", ""),
                expected_discharge_date=request.data.get("expected_discharge_date") or None,
            )
        except BedManagementError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            BedAssignmentSerializer(assignment).data if assignment else BedSerializer(bed).data,
            status=200,
        )

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, pk=None):
        require_permission(request.user, "inpatient.release_bed", "admissions.assign_bed")
        bed = self.get_object()
        admission = bed.current_admission
        if not admission:
            return Response({"detail": "This bed has no active patient assignment."}, status=400)
        try:
            assignment = release_bed(
                admission,
                request.user,
                reason=request.data.get("reason", "Released"),
                set_cleaning=bool(request.data.get("set_cleaning", False)),
            )
        except BedManagementError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BedAssignmentSerializer(assignment).data, status=200)


class BedAssignmentViewSet(viewsets.ModelViewSet):
    """Bed assignment history. Creation goes through the bed management service."""

    queryset = BedAssignment.objects.select_related(
        "admission__patient", "bed__room__ward", "assigned_by", "released_by"
    ).all()
    serializer_class = BedAssignmentSerializer
    permission_classes = [HasPermission]
    code = "inpatient.view"
    write_code = "inpatient.manage_beds"
    filterset_fields = ["admission", "bed", "ward", "room", "assigned_by"]
    search_fields = ["admission__patient__first_name", "admission__patient__last_name",
                     "admission__admission_number", "bed__bed_number"]
    ordering_fields = ["assigned_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.in_roles("patient"):
            return qs.filter(admission__in=_patient_admissions(self.request.user))
        if self.request.user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(self.request.user))
        if self.request.user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(self.request.user))
        return qs


class TransferViewSet(viewsets.ReadOnlyModelViewSet):
    """History of patient bed transfers."""

    serializer_class = TransferSerializer
    permission_classes = [HasPermission]
    code = "inpatient.view"
    filterset_fields = ["admission", "ward"]
    search_fields = ["admission__patient__first_name", "admission__patient__last_name",
                     "admission__admission_number", "bed__bed_number"]
    ordering_fields = ["assigned_at"]
    ordering = ["-assigned_at"]

    def get_queryset(self):
        qs = BedAssignment.objects.filter(
            released_at__isnull=False, release_reason__startswith="Transfer"
        ).select_related("admission__patient", "bed__room__ward", "assigned_by")
        if self.request.user.in_roles("patient"):
            return qs.filter(admission__in=_patient_admissions(self.request.user))
        if self.request.user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(self.request.user))
        if self.request.user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(self.request.user))
        return qs


class AdmissionViewSet(viewsets.ModelViewSet):
    queryset = Admission.objects.select_related(
        "patient", "doctor", "assigned_nurse", "department", "ward", "room", "bed"
    ).all()
    serializer_class = AdmissionSerializer
    permission_classes = [InpatientActionPermission]
    code = "admissions.view"
    write_code = "admissions.update"
    filterset_fields = ["status", "patient", "doctor", "department", "ward", "bed", "assigned_nurse"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number",
                     "admission_number"]
    ordering_fields = ["admission_date"]

    def get_queryset(self):
        return _role_scoped_admissions(self.request.user)

    def perform_create(self, serializer):
        admission = serializer.save(created_by=self.request.user)
        if admission.bed_id:
            try:
                assign_patient_to_bed(
                    admission, admission.bed, self.request.user,
                    expected_discharge_date=admission.expected_discharge_date,
                )
            except BedManagementError as exc:
                admission.soft_delete(self.request.user)
                raise ValidationError({"bed": str(exc)})
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.admission",
                  record=str(admission.patient), object_id=admission.id,
                  request=self.request, new_value=serializer.data)
        if admission.patient.user:
            notify(admission.patient.user, "You have been admitted",
                   f"Admitted to {admission.ward.name if admission.ward else 'the ward'}.",
                   notification_type="admission", link="/portal")

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Transfer the patient to a new bed, freeing the previous bed."""
        require_permission(request.user, "inpatient.transfer", "admissions.transfer",
                           "admissions.assign_bed")
        admission = Admission.objects.select_for_update().filter(pk=pk).first()
        if not admission:
            return Response({"detail": "The requested record could not be found."}, status=404)
        new_bed_id = request.data.get("bed")
        if not new_bed_id:
            return Response({"detail": "A target bed is required for a transfer."}, status=400)
        new_bed = Bed.objects.filter(pk=new_bed_id).first()
        if not new_bed:
            return Response({"detail": "Target bed not found."}, status=404)
        try:
            assignment = transfer_patient_bed(
                admission, new_bed, request.user,
                reason=request.data.get("reason", "Transfer"),
                notes=request.data.get("notes", ""),
            )
        except BedManagementError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(BedAssignmentSerializer(assignment).data, status=200)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def assign_nurse(self, request, pk=None):
        require_permission(request.user, "inpatient.manage_beds", "inpatient.assign_bed")
        admission = Admission.objects.select_for_update().filter(pk=pk).first()
        if not admission:
            return Response({"detail": "The requested record could not be found."}, status=404)
        nurse_id = request.data.get("nurse")
        if not nurse_id:
            return Response({"detail": "nurse is required."}, status=400)
        nurse = User.objects.filter(pk=nurse_id).first()
        if not nurse:
            return Response({"detail": "Nurse not found."}, status=404)
        active = NurseAssignment.objects.filter(
            admission=admission, nurse_id=nurse_id, unassigned_at__isnull=True
        ).first()
        if active:
            return Response(
                {"detail": "This nurse already has an active assignment for this admission."},
                status=400,
            )
        assignment = assign_nurse_to_admission(
            admission, nurse, request.user,
            role=request.data.get("role", NurseAssignment.ROLE_PRIMARY),
            notes=request.data.get("notes", ""),
        )
        if assignment.admission.assigned_nurse_id:
            notify(assignment.admission.assigned_nurse, "Patient assigned to you",
                   f"{assignment.admission.patient.full_name} is now under your care.",
                   notification_type="bed_assignment", link="/inpatient/bed-board",
                   related_module="inpatient", related_object_id=assignment.admission_id)
        return Response(NurseAssignmentSerializer(assignment).data, status=201)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """Chronological inpatient journey for the admission."""
        admission = Admission.objects.filter(pk=pk).first()
        if not admission:
            return Response({"detail": "The requested record could not be found."}, status=404)
        return Response(build_patient_timeline(admission))


class NurseAssignmentViewSet(viewsets.ModelViewSet):
    queryset = NurseAssignment.objects.select_related("admission__patient", "nurse", "assigned_by").all()
    serializer_class = NurseAssignmentSerializer
    permission_classes = [HasPermission]
    code = "inpatient.view"
    write_code = "inpatient.manage_beds"
    filterset_fields = ["admission", "nurse", "role"]
    ordering_fields = ["assigned_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.in_roles("patient"):
            return qs.filter(admission__in=_patient_admissions(self.request.user))
        if self.request.user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(self.request.user))
        if self.request.user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(self.request.user))
        return qs

    def perform_create(self, serializer):
        assignment = serializer.save(assigned_by=self.request.user, created_by=self.request.user)
        if assignment.role == NurseAssignment.ROLE_PRIMARY:
            admission = assignment.admission
            admission.assigned_nurse = assignment.nurse
            admission.save(update_fields=["assigned_nurse", "updated_at"])
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.nurseassignment",
                  record=str(assignment.admission), object_id=assignment.id, request=self.request)
        notify(assignment.nurse, "Patient assigned to you",
               f"{assignment.admission.patient.full_name} is now under your care.",
               notification_type="bed_assignment", link="/inpatient/bed-board",
               related_module="inpatient", related_object_id=assignment.admission_id)


class NursingNoteViewSet(viewsets.ModelViewSet):
    queryset = NursingNote.objects.select_related(
        "admission__patient", "nurse", "ward", "bed"
    ).all()
    serializer_class = NursingNoteSerializer
    permission_classes = [InpatientActionPermission]
    code = "nursing.view"
    create_code = "nursing.create"
    write_code = "nursing.update"
    delete_code = "nursing.delete"
    filterset_fields = ["admission", "nurse", "status", "shift_type", "condition"]
    search_fields = ["admission__patient__first_name", "admission__patient__last_name",
                     "admission__admission_number", "note", "observations"]
    ordering_fields = ["recorded_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user))
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user)) | qs.filter(nurse=user)
        return qs.distinct()

    def perform_create(self, serializer):
        status_value = serializer.validated_data.get("status", NursingNote.STATUS_DRAFT)
        note = serializer.save(nurse=self.request.user, created_by=self.request.user)
        if note.ward_id is None and note.admission.ward_id:
            note.ward_id = note.admission.ward_id
            note.save(update_fields=["ward"])
        if status_value == NursingNote.STATUS_SUBMITTED:
            note.submit(self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.nursingnote",
                  record=str(note.admission), object_id=note.id, request=self.request,
                  new_value={"status": note.status})

    def update(self, request, *args, **kwargs):
        note = self.get_object()
        if note.status != NursingNote.STATUS_DRAFT:
            return Response(
                {"detail": "Submitted notes cannot be edited. Use the amend action to record a correction."},
                status=403,
            )
        return super().update(request, *args, **kwargs)

    partial_update = update

    def perform_destroy(self, instance):
        if instance.status != NursingNote.STATUS_DRAFT:
            return Response(
                {"detail": "Submitted clinical notes cannot be deleted."}, status=403
            )
        audit_log(self.request.user, AuditLog.ACTION_DELETE, "inpatient.nursingnote",
                  record=str(instance.admission), object_id=instance.id, request=self.request)
        instance.soft_delete(self.request.user)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        require_permission(request.user, "nursing.submit", "nursing.create")
        note = self.get_object()
        if note.status != NursingNote.STATUS_DRAFT:
            return Response({"detail": "Only draft notes can be submitted."}, status=400)
        note.submit(request.user)
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inpatient.nursingnote",
                  record=str(note.admission), object_id=note.id, request=request,
                  description="nursing note submitted")
        return Response(NursingNoteSerializer(note).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def amend(self, request, pk=None):
        require_permission(request.user, "nursing.amend")
        note = self.get_object()
        if note.status == NursingNote.STATUS_DRAFT:
            return Response({"detail": "Draft notes can be edited directly instead of amended."}, status=400)
        reason = request.data.get("reason", "")
        if not reason.strip():
            return Response({"detail": "A reason is required for an amendment."}, status=400)

        editable = [
            "note", "observations", "condition", "consciousness", "pain_assessment", "pain_score",
            "mobility", "nutrition_intake", "fluid_intake_ml", "fluid_output_ml",
            "medication_observations", "wound_dressing_observations", "patient_complaints",
            "interventions", "patient_response", "safety_concerns", "fall_risk",
            "doctor_instructions", "pending_tasks", "handover_current_condition",
            "handover_recent_changes", "handover_interventions_provided",
            "handover_pending_tasks", "handover_important_observations",
            "handover_follow_up_required",
        ]
        changed_fields = {}
        for field in editable:
            if field in request.data:
                changed_fields[field] = request.data[field]

        snapshot = {}
        for field in changed_fields:
            snapshot[field] = getattr(note, field)
        if not changed_fields:
            return Response({"detail": "No editable fields provided for the amendment."}, status=400)

        amended = note.amend(request.user, reason, changed_fields, snapshot)
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inpatient.nursingnote",
                  record=str(note.admission), object_id=amended.id, request=request,
                  previous_value=snapshot, new_value=changed_fields,
                  description="nursing note amended")
        return Response(NursingNoteSerializer(amended).data)


class NursingHandoverViewSet(viewsets.ModelViewSet):
    queryset = NursingHandover.objects.select_related(
        "admission__patient", "nurse", "incoming_nurse", "ward", "bed"
    ).all()
    serializer_class = NursingHandoverSerializer
    permission_classes = [InpatientActionPermission]
    code = "nursing.view"
    create_code = "nursing.handover"
    write_code = "nursing.update"
    delete_code = "nursing.delete"
    filterset_fields = ["admission", "nurse", "incoming_nurse", "ward", "shift_type",
                        "handover_date", "condition"]
    search_fields = ["admission__patient__first_name", "admission__patient__last_name",
                     "admission__admission_number"]
    ordering_fields = ["recorded_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user))
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user)) | qs.filter(nurse=user)
        return qs.distinct()

    def perform_create(self, serializer):
        handover = serializer.save(nurse=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.handover",
                  record=str(handover.admission), object_id=handover.id, request=self.request)
        if handover.incoming_nurse_id and handover.incoming_nurse_id != self.request.user.id:
            notify(handover.incoming_nurse, "New shift handover available",
                   f"A handover is available for {handover.admission.patient.full_name} ({handover.ward.name if handover.ward else 'ward'}).",
                   notification_type="handover", link="/nursing/handover",
                   related_module="nursing", related_object_id=handover.id,
                   priority=Notification.PRIORITY_HIGH)

    @action(detail=False, methods=["get"])
    def my_handovers(self, request):
        """Handovers directed to the current user (incoming nurse)."""
        qs = NursingHandover.objects.filter(incoming_nurse=request.user).select_related(
            "admission__patient", "nurse", "incoming_nurse", "ward", "bed"
        )
        return Response(NursingHandoverSerializer(qs, many=True).data)


class ICUMonitoringSheetViewSet(viewsets.ModelViewSet):
    queryset = ICUMonitoringSheet.objects.select_related("admission__patient", "bed", "nurse", "doctor").all()
    serializer_class = ICUMonitoringSheetSerializer
    permission_classes = [HasPermission]
    code = "icu.view"
    create_code = "icu.create"
    write_code = "icu.update"
    filterset_fields = ["admission", "bed", "nurse", "doctor", "monitoring_date", "period", "status"]
    search_fields = ["admission__patient__first_name", "admission__patient__last_name",
                     "admission__admission_number"]
    ordering_fields = ["monitoring_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user))
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user))
        return qs

    def perform_create(self, serializer):
        sheet = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.icusheet",
                  record=str(sheet.admission), object_id=sheet.id, request=self.request)


class ICUMonitoringRecordViewSet(viewsets.ModelViewSet):
    queryset = ICUMonitoringRecord.objects.select_related("admission__patient", "nurse", "sheet").all()
    serializer_class = ICUMonitoringRecordSerializer
    permission_classes = [HasPermission]
    code = "icu.view"
    create_code = "icu.create"
    write_code = "icu.update"
    filterset_fields = ["admission", "sheet", "nurse", "frequency"]
    ordering_fields = ["recorded_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user))
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user))
        return qs

    def perform_create(self, serializer):
        record = serializer.save(nurse=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.icu",
                  record=str(record.admission), object_id=record.id, request=self.request,
                  new_value={"recorded_at": record.recorded_at.isoformat()})
        self._notify_critical_alerts(record)

    def _notify_critical_alerts(self, record):
        from apps.inpatient.services import evaluate_icu_record_alerts

        alerts = evaluate_icu_record_alerts(record)
        critical = [a for a in alerts if a["severity"] == ICUThreshold.SEVERITY_CRITICAL]
        if not critical:
            return
        recipients = set()
        if record.admission.assigned_nurse_id:
            recipients.add(record.admission.assigned_nurse_id)
        if record.admission.doctor_id:
            recipients.add(record.admission.doctor_id)
        if record.nurse_id:
            recipients.add(record.nurse_id)
        detail = ", ".join(f"{a['parameter_name']} {a['value']}{a['unit'] or ''}" for a in critical)
        for user_id in recipients:
            try:
                from apps.accounts.models import User

                target = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                continue
            notify(target, "ICU alert",
                   f"Critical observation for {record.admission.patient.full_name}: {detail}.",
                   notification_type="icu_alert", link="/icu/monitoring",
                   related_module="icu", related_object_id=record.id,
                   priority=Notification.PRIORITY_URGENT)


class FluidBalanceViewSet(viewsets.ModelViewSet):
    queryset = FluidBalance.objects.select_related("admission__patient", "nurse").all()
    serializer_class = FluidBalanceSerializer
    permission_classes = [HasPermission]
    code = "nursing.view"
    create_code = "icu.record_fluid"
    write_code = "icu.record_fluid"
    filterset_fields = ["admission", "nurse", "balance_date", "period"]
    ordering_fields = ["balance_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user))
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user))
        return qs

    def perform_create(self, serializer):
        record = serializer.save(nurse=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.fluidbalance",
                  record=str(record.admission), object_id=record.id, request=self.request,
                  new_value={"balance_date": str(record.balance_date), "period": record.period})


class ICUThresholdViewSet(viewsets.ModelViewSet):
    """Configurable clinical alert thresholds; managed by clinical administrators."""

    queryset = ICUThreshold.objects.all()
    serializer_class = ICUThresholdSerializer
    permission_classes = [InpatientActionPermission]
    code = "icu.view"
    create_code = "icu.manage_thresholds"
    write_code = "icu.manage_thresholds"
    delete_code = "icu.manage_thresholds"
    filterset_fields = ["parameter", "is_active"]


class DischargeViewSet(viewsets.ModelViewSet):
    queryset = Discharge.objects.select_related("admission", "patient").all()
    serializer_class = DischargeSerializer
    permission_classes = [InpatientActionPermission]
    code = "admissions.discharge"
    create_code = "admissions.discharge"
    write_code = "admissions.update"
    delete_code = "admissions.update"
    filterset_fields = ["patient", "discharge_type", "follow_up_date"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["discharge_date"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        admission_id = request.data.get("admission")
        admission = Admission.objects.select_for_update().filter(pk=admission_id).first()
        if not admission:
            return Response({"detail": "Admission not found."}, status=404)
        if admission.status == Admission.STATUS_DISCHARGED:
            return Response({"detail": "This admission has already been discharged."}, status=400)

        discharge = Discharge.objects.create(
            admission=admission,
            patient=admission.patient,
            discharge_type=request.data.get("discharge_type", "home"),
            diagnosis_summary=request.data.get("diagnosis_summary", ""),
            treatment_summary=request.data.get("treatment_summary", ""),
            medication=request.data.get("medication", ""),
            outstanding_bills=request.data.get("outstanding_bills", ""),
            follow_up_instructions=request.data.get("follow_up_instructions", ""),
            follow_up_date=request.data.get("follow_up_date") or None,
            doctor_notes=request.data.get("doctor_notes", ""),
            discharged_by=request.user,
            created_by=request.user,
        )
        admission.status = Admission.STATUS_DISCHARGED
        admission.discharged_at = timezone.now()
        admission.save()
        if admission.bed_id:
            from apps.inpatient.services import BedManagementError, release_bed

            try:
                release_bed(admission, request.user, reason="Discharged")
            except BedManagementError:
                pass

        audit_log(request.user, AuditLog.ACTION_CREATE, "inpatient.discharge",
                  record=str(admission.patient), object_id=discharge.id,
                  request=request, description="discharged patient")
        if admission.patient.user:
            notify(admission.patient.user, "Discharged",
                   "You have been discharged. Please follow the instructions provided.",
                   notification_type="discharge", link="/portal")
        return Response(DischargeSerializer(discharge).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """Download the discharge summary as a PDF."""
        discharge = self.get_object()
        from apps.inpatient.services import build_discharge_summary_pdf

        buffer = build_discharge_summary_pdf(discharge)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="discharge_{discharge.patient.patient_number}.pdf"'
        )
        return response


class InpatientStatsView(APIView):
    """Role-aware inpatient statistics for the dashboard."""

    permission_classes = [HasPermission]
    code = "dashboard.view"

    def _latest_vitals_with_alerts(self):
        from apps.inpatient.services import evaluate_icu_record_alerts

        threshold_params = set(
            ICUThreshold.objects.filter(is_active=True).values_list("parameter", flat=True)
        )
        if not threshold_params:
            return 0
        admitted = Admission.objects.filter(status=Admission.STATUS_ADMITTED)
        count = 0
        for admission in admitted:
            latest = admission.vital_signs.order_by("-recorded_at").first()
            if not latest:
                continue
            candidates = {
                "heart_rate": latest.pulse,
                "temperature": float(latest.temperature) if latest.temperature is not None else None,
                "bp_systolic": latest.blood_pressure_systolic,
                "bp_diastolic": latest.blood_pressure_diastolic,
                "respiratory_rate": latest.respiratory_rate,
                "spo2": latest.oxygen_saturation,
                "blood_glucose": float(latest.blood_glucose) if latest.blood_glucose is not None else None,
                "pain_score": latest.pain_score,
            }
            threshold_values = {
                p: ICUThreshold.objects.filter(parameter=p).first() for p in threshold_params
            }
            flagged = False
            for parameter, value in candidates.items():
                threshold = threshold_values.get(parameter)
                if threshold and threshold.evaluate(value):
                    flagged = True
                    break
            if flagged:
                count += 1
        return count

    def get(self, request):
        today = timezone.localdate()
        admitted = Admission.objects.filter(status=Admission.STATUS_ADMITTED)
        beds = Bed.objects.all()

        stats = {
            "total_beds": beds.count(),
            "available_beds": beds.filter(status=Bed.STATUS_AVAILABLE).count(),
            "occupied_beds": beds.filter(status=Bed.STATUS_OCCUPIED).count(),
            "reserved_beds": beds.filter(status=Bed.STATUS_RESERVED).count(),
            "admitted_patients": admitted.count(),
            "active_icu_patients": admitted.filter(ward__ward_type=Ward.TYPE_ICU).count(),
            "pending_handovers": NursingHandover.objects.filter(handover_date=today).count(),
            "recent_vitals_count": VitalSigns.objects.filter(
                recorded_at__date=today
            ).count(),
            "patients_requiring_attention": self._latest_vitals_with_alerts(),
        }

        user = request.user
        if user.in_roles("nurse", "icu_nurse"):
            mine = _nurse_admissions(user).filter(status=Admission.STATUS_ADMITTED)
            stats["my_assigned_patients"] = mine.count()
            stats["my_current_shift"] = None
            from apps.scheduling.models import NurseShift

            shift = (
                NurseShift.objects.filter(
                    nurse=user, shift_date=today,
                    status__in=[NurseShift.STATUS_SCHEDULED, NurseShift.STATUS_ACTIVE],
                )
                .order_by("start_time")
                .first()
            )
            if shift:
                stats["my_current_shift"] = (
                    f"{shift.get_shift_type_display()} {shift.start_time:%H:%M}-{shift.end_time:%H:%M}"
                )
            stats["pending_vitals"] = sum(
                1 for a in mine if not a.vital_signs.filter(recorded_at__gte=timezone.now() - timezone.timedelta(hours=8)).exists()
            )
            stats["pending_handovers"] = NursingHandover.objects.filter(
                handover_date=today, incoming_nurse__isnull=True,
            ).filter(admission__in=mine).count()
        elif user.in_roles("doctor"):
            mine = _doctor_admissions(user).filter(status=Admission.STATUS_ADMITTED)
            stats["my_inpatients"] = mine.count()
            stats["patients_requiring_review"] = self._latest_vitals_with_alerts()
            stats["pending_results"] = 0
            try:
                from apps.laboratory.models import LabRequest

                stats["pending_results"] = LabRequest.objects.filter(
                    doctor=user,
                    status__in=["requested", "sample_collected", "processing"],
                ).count()
            except Exception:
                pass

        return Response(stats)


class TimelineExportView(APIView):
    """Admission timeline for a patient across their admissions (authorized only)."""

    permission_classes = [HasPermission]
    code = "inpatient.view"

    def get(self, request):
        patient = request.query_params.get("patient")
        if not patient:
            return Response({"detail": "patient query param is required."}, status=400)
        from apps.patients.models import Patient

        patient_obj = Patient.objects.filter(pk=patient).first()
        if not patient_obj:
            return Response({"detail": "Patient not found."}, status=404)
        if request.user.in_roles("patient") and (
            not patient_obj.user or patient_obj.user_id != request.user.id
        ):
            return Response({"detail": "Not permitted."}, status=403)
        admissions = Admission.objects.filter(patient=patient_obj)
        events = []
        for admission in admissions:
            events.extend(build_patient_timeline(admission))
        events.sort(key=lambda e: e["timestamp"])
        return Response(events)


class InpatientVitalsViewSet(viewsets.ModelViewSet):
    """Digital vitals log for inpatient monitoring.

    Extends the core clinical vitals endpoint with inpatient-specific
    filters (admission, ward, date range) and CSV export for authorized users.
    """

    from apps.clinical.serializers import VitalSignsSerializer

    serializer_class = VitalSignsSerializer
    permission_classes = [HasPermission]
    code = "vitals.view"
    create_code = "vitals.create"
    write_code = "vitals.create"
    filterset_fields = ["patient", "consultation", "admission"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["recorded_at"]

    def get_queryset(self):
        qs = VitalSigns.objects.select_related("patient", "admission", "recorded_by").all()
        params = self.request.query_params
        if params.get("admission"):
            qs = qs.filter(admission_id=params["admission"])
        if params.get("ward"):
            qs = qs.filter(admission__ward_id=params["ward"])
        if params.get("recorded_at__date"):
            qs = qs.filter(recorded_at__date=params["recorded_at__date"])
        if params.get("recorded_at__gte"):
            qs = qs.filter(recorded_at__gte=params["recorded_at__gte"])
        if params.get("recorded_at__lte"):
            qs = qs.filter(recorded_at__lte=params["recorded_at__lte"])
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        if user.in_roles("doctor"):
            return qs.filter(admission__in=_doctor_admissions(user)) | qs.filter(
                consultation__doctor=user, admission__isnull=True
            )
        if user.in_roles("nurse", "icu_nurse"):
            return qs.filter(admission__in=_nurse_admissions(user))
        return qs

    def perform_create(self, serializer):
        vital = serializer.save(recorded_by=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "clinical.vitals",
                  record=str(vital.patient), object_id=vital.id, request=self.request,
                  new_value={"admission": vital.admission_id, "recorded_at": vital.recorded_at.isoformat()})
        self._notify_doctor(vital)

    def _notify_doctor(self, vital):
        admission = vital.admission
        if not admission:
            return
        recipients = set()
        if admission.doctor_id:
            recipients.add(admission.doctor_id)
        if admission.assigned_nurse_id:
            recipients.add(admission.assigned_nurse_id)
        bp = ""
        if vital.blood_pressure_systolic:
            bp = f"{vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}"
        summary = ", ".join(filter(None, [
            f"BP {bp}" if bp else "",
            f"HR {vital.pulse}" if vital.pulse else "",
            f"SpO2 {vital.oxygen_saturation}%" if vital.oxygen_saturation else "",
        ]))
        for user_id in recipients:
            try:
                from apps.accounts.models import User

                target = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                continue
            notify(target, "New vital signs recorded",
                   f"New vitals recorded for {vital.patient.full_name}: {summary}.",
                   notification_type="vitals", link="/inpatient/vitals",
                   related_module="vitals", related_object_id=vital.id)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Historical vital signs ordered oldest-first for charting."""
        patient = request.query_params.get("patient")
        if not patient:
            return Response({"detail": "patient query param is required."}, status=400)
        qs = self.get_queryset().filter(patient_id=patient).order_by("recorded_at")
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """CSV export of the filtered vitals log for authorized users."""
        if request.user.in_roles("patient"):
            raise PermissionDenied("Patients cannot export the vitals log.")
        require_permission(request.user, "reports.export", "vitals.view")
        import csv

        qs = self.filter_queryset(self.get_queryset()).order_by("recorded_at")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="vitals_log.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "datetime", "patient_number", "patient", "admission", "ward",
            "temperature", "bp_systolic", "bp_diastolic", "pulse",
            "respiratory_rate", "spo2", "weight", "height", "pain_score",
            "blood_glucose", "notes", "recorded_by",
        ])
        for v in qs:
            writer.writerow([
                v.recorded_at.isoformat(),
                v.patient.patient_number,
                v.patient.full_name,
                v.admission.admission_number if v.admission else "",
                v.admission.ward.name if v.admission and v.admission.ward else "",
                v.temperature,
                v.blood_pressure_systolic,
                v.blood_pressure_diastolic,
                v.pulse,
                v.respiratory_rate,
                v.oxygen_saturation,
                v.weight,
                v.height,
                v.pain_score,
                v.blood_glucose,
                v.notes,
                v.recorded_by.get_full_name() if v.recorded_by else "",
            ])
        return response


class NursingDashboardView(APIView):
    """Aggregated snapshot of the nursing workload for a logged-in nurse."""

    permission_classes = [HasPermission]
    code = "nursing.view"

    def get(self, request):
        user = request.user
        my_admissions = _nurse_admissions(user)
        assigned_beds = Bed.objects.filter(current_admission__in=my_admissions)
        notes_today = NursingNote.objects.filter(
            nurse=user, recorded_at__date=timezone.localdate()
        ).count()
        pending_notes = NursingNote.objects.filter(
            nurse=user, status=NursingNote.STATUS_DRAFT
        ).count()
        handovers_today = NursingHandover.objects.filter(
            nurse=user, recorded_at__date=timezone.localdate()
        ).count()
        today = timezone.localdate()
        shifts_today = user.shifts.filter(date=today).count()
        return Response({
            "patients": my_admissions.count(),
            "beds": assigned_beds.count(),
            "ward": (assigned_beds.first().ward.name if assigned_beds.first() else None),
            "notes_today": notes_today,
            "pending_notes": pending_notes,
            "handovers_today": handovers_today,
            "shifts_today": shifts_today,
        })
