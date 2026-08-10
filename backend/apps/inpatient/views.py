from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify
from apps.inpatient.models import Admission, Bed, Discharge, NursingNote, Room, Ward
from apps.inpatient.serializers import (
    AdmissionSerializer,
    BedSerializer,
    DischargeSerializer,
    NursingNoteSerializer,
    RoomSerializer,
    WardSerializer,
)


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
    permission_classes = [HasPermission]
    code = "admissions.view"
    write_code = "admissions.update"
    filterset_fields = ["status", "room", "room__ward"]

    @action(detail=False, methods=["get"])
    def board(self, request):
        """Visual bed-management board grouped by ward."""
        result = []
        for ward in Ward.objects.all():
            beds = Bed.objects.filter(room__ward=ward).select_related("room")
            result.append({
                "ward": {"id": ward.id, "name": ward.name, "type": ward.ward_type},
                "beds": BedSerializer(beds, many=True).data,
            })
        return Response(result)

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        bed = self.get_object()
        new_status = request.data.get("status")
        if new_status not in dict(Bed.STATUS_CHOICES):
            return Response({"detail": "Invalid bed status."}, status=400)
        bed.status = new_status
        bed.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inpatient.bed",
                  record=str(bed), object_id=bed.id, request=request,
                  description=f"status set to {new_status}")
        return Response(BedSerializer(bed).data)


class AdmissionViewSet(viewsets.ModelViewSet):
    queryset = Admission.objects.select_related("patient", "doctor", "department", "ward", "room", "bed").all()
    serializer_class = AdmissionSerializer
    permission_classes = [HasPermission]
    code = "admissions.view"
    write_code = "admissions.update"
    filterset_fields = ["status", "patient", "doctor", "department", "ward", "bed"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["admission_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        admission = serializer.save(created_by=self.request.user)
        if admission.bed:
            admission.bed.status = Bed.STATUS_OCCUPIED
            admission.bed.save(update_fields=["status"])
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.admission",
                  record=str(admission.patient), object_id=admission.id,
                  request=self.request, new_value=serializer.data)
        if admission.patient.user:
            notify(admission.patient.user, "You have been admitted",
                   f"Admitted to {admission.ward.name if admission.ward else 'ward'}.",
                   notification_type="admission", link="/portal")

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Transfer the patient to a new ward/room/bed, freeing the previous bed."""
        admission = self.get_object()
        new_ward = request.data.get("ward")
        new_room = request.data.get("room")
        new_bed = request.data.get("bed")
        if not (new_ward and new_room and new_bed):
            return Response({"detail": "ward, room and bed are required for a transfer."}, status=400)
        old_bed = admission.bed
        if old_bed:
            Bed.objects.filter(pk=old_bed.id).update(status=Bed.STATUS_AVAILABLE)
        new_bed_obj = Bed.objects.select_for_update().get(pk=new_bed)
        if new_bed_obj.status == Bed.STATUS_OCCUPIED:
            return Response({"detail": "The target bed is already occupied."}, status=400)
        admission.ward_id = new_ward
        admission.room_id = new_room
        admission.bed_id = new_bed
        admission.status = Admission.STATUS_TRANSFERRED
        admission.save()
        new_bed_obj.status = Bed.STATUS_OCCUPIED
        new_bed_obj.save(update_fields=["status"])
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inpatient.admission",
                  record=str(admission.patient), object_id=admission.id, request=request,
                  description=f"transferred to bed {new_bed_obj.bed_number}")
        return Response(AdmissionSerializer(admission).data)


class NursingNoteViewSet(viewsets.ModelViewSet):
    queryset = NursingNote.objects.select_related("admission", "nurse").all()
    serializer_class = NursingNoteSerializer
    permission_classes = [HasPermission]
    code = "vitals.create"
    filterset_fields = ["admission"]
    ordering_fields = ["recorded_at"]

    def perform_create(self, serializer):
        note = serializer.save(nurse=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inpatient.nursingnote",
                  record=str(note.admission), object_id=note.id, request=self.request)


class DischargeViewSet(viewsets.ModelViewSet):
    queryset = Discharge.objects.select_related("admission", "patient").all()
    serializer_class = DischargeSerializer
    permission_classes = [HasPermission]
    code = "admissions.discharge"
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
        if admission.bed:
            Bed.objects.filter(pk=admission.bed_id).update(status=Bed.STATUS_AVAILABLE)

        audit_log(request.user, AuditLog.ACTION_CREATE, "inpatient.discharge",
                  record=str(admission.patient), object_id=discharge.id,
                  request=request, description=f"discharged patient")
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
