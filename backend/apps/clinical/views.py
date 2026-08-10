from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.clinical.models import (
    Consultation,
    Diagnosis,
    Prescription,
    Referral,
    VitalSigns,
)
from apps.clinical.serializers import (
    ConsultationSerializer,
    DiagnosisSerializer,
    PrescriptionSerializer,
    ReferralSerializer,
    VitalSignsSerializer,
)
from apps.core.models import AuditLog
from apps.core.services import audit_log


class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.select_related("patient", "doctor", "appointment").all()
    serializer_class = ConsultationSerializer
    permission_classes = [HasPermission]
    code = "consultations.view"
    write_code = "consultations.update"
    filterset_fields = ["status", "doctor", "patient", "appointment", "follow_up_date"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number",
                     "chief_complaint", "clinical_notes"]
    ordering_fields = ["recorded_at", "follow_up_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(doctor=user)
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def get_queryset_for_write(self, obj):
        """Doctors may only modify consultations they own."""
        user = self.request.user
        if user.in_roles("doctor") and obj.doctor_id != user.id:
            return False
        return True

    def perform_update(self, serializer):
        if not self.get_queryset_for_write(serializer.instance):
            from rest_framework import exceptions

            raise exceptions.PermissionDenied("You can only modify your own consultations.")
        previous = {"status": serializer.instance.status}
        consultation = serializer.save(updated_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_UPDATE, "clinical.consultation",
                  record=str(consultation.patient), object_id=consultation.id,
                  request=self.request, previous_value=previous, new_value=serializer.data)

    def perform_create(self, serializer):
        consultation = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "clinical.consultation",
                  record=str(consultation.patient), object_id=consultation.id,
                  request=self.request, new_value=serializer.data)

    def perform_destroy(self, instance):
        audit_log(self.request.user, AuditLog.ACTION_DELETE, "clinical.consultation",
                  record=str(instance.patient), object_id=instance.id, request=self.request)
        instance.soft_delete(self.request.user)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        consultation = self.get_object()
        if not self.get_queryset_for_write(consultation):
            from rest_framework import exceptions

            raise exceptions.PermissionDenied("You can only modify your own consultations.")
        consultation.status = Consultation.STATUS_COMPLETED
        consultation.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "clinical.consultation",
                  record=str(consultation.patient), object_id=consultation.id,
                  request=request, description="consultation completed")
        return Response(ConsultationSerializer(consultation).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def request_lab(self, request, pk=None):
        """Request laboratory tests for the patient from within the consultation."""
        consultation = self.get_object()
        from apps.laboratory.models import LabRequest, LabRequestItem

        tests = request.data.get("tests", [])
        if not tests:
            return Response({"detail": "Please provide at least one test id."}, status=400)
        lab_request = LabRequest.objects.create(
            patient=consultation.patient,
            doctor=request.user,
            consultation=consultation,
            priority=request.data.get("priority", "routine"),
        )
        for test_id in tests:
            LabRequestItem.objects.create(lab_request=lab_request, test_id=test_id)
        audit_log(request.user, AuditLog.ACTION_CREATE, "laboratory.labrequest",
                  record=str(consultation.patient), object_id=lab_request.id,
                  request=request, description="lab tests requested from consultation")
        from apps.laboratory.serializers import LabRequestSerializer

        return Response(LabRequestSerializer(lab_request).data, status=201)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def schedule_followup(self, request, pk=None):
        consultation = self.get_object()
        from apps.appointments.models import Appointment

        appointment = Appointment.objects.create(
            patient=consultation.patient,
            doctor=request.data.get("doctor") or consultation.doctor_id,
            department=request.data.get("department") or consultation.doctor.department_id,
            appointment_date=request.data.get("appointment_date"),
            start_time=request.data.get("start_time"),
            end_time=request.data.get("end_time"),
            reason=request.data.get("reason") or f"Follow-up for {consultation.chief_complaint or 'consultation'}",
            priority=request.data.get("priority", "routine"),
        )
        consultation.follow_up_date = request.data.get("appointment_date")
        consultation.save(update_fields=["follow_up_date"])
        audit_log(request.user, AuditLog.ACTION_CREATE, "appointments.appointment",
                  record=str(consultation.patient), object_id=appointment.id,
                  request=request, description="follow-up appointment created")
        from apps.appointments.serializers import AppointmentSerializer

        return Response(AppointmentSerializer(appointment).data, status=201)


class VitalSignsViewSet(viewsets.ModelViewSet):
    queryset = VitalSigns.objects.select_related("patient").all()
    serializer_class = VitalSignsSerializer
    permission_classes = [HasPermission]
    code = "vitals.view"
    write_code = "vitals.create"
    filterset_fields = ["patient", "consultation"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["recorded_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        vital = serializer.save(recorded_by=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "clinical.vitals",
                  record=str(vital.patient), object_id=vital.id, request=self.request)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Historical vital signs for a patient, ordered oldest-first for charting."""
        patient = request.query_params.get("patient")
        if not patient:
            return Response({"detail": "patient query param is required."}, status=400)
        qs = VitalSigns.objects.filter(patient_id=patient).order_by("recorded_at")
        return Response(VitalSignsSerializer(qs, many=True).data)


class DiagnosisViewSet(viewsets.ModelViewSet):
    queryset = Diagnosis.objects.select_related("patient", "consultation").all()
    serializer_class = DiagnosisSerializer
    permission_classes = [HasPermission]
    code = "consultations.view"
    write_code = "consultations.update"
    filterset_fields = ["patient", "consultation", "is_primary"]
    search_fields = ["name", "icd_code"]
    ordering_fields = ["id"]


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.select_related("patient", "doctor").all()
    serializer_class = PrescriptionSerializer
    permission_classes = [HasPermission]
    code = "consultations.prescribe"
    filterset_fields = ["status", "patient", "doctor", "consultation"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        prescription = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "pharmacy.prescription",
                  record=str(prescription.patient), object_id=prescription.id,
                  request=self.request, description="prescription created")
        if prescription.patient.user:
            from apps.core.services import notify

            notify(prescription.patient.user, "New prescription",
                   f"Your prescription has been created. Visit the pharmacy to collect.",
                   notification_type="prescription", link="/portal")

    def perform_update(self, serializer):
        prescription = serializer.save(updated_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_UPDATE, "pharmacy.prescription",
                  record=str(prescription.patient), object_id=prescription.id,
                  request=self.request, description="prescription modified")


class ReferralViewSet(viewsets.ModelViewSet):
    queryset = Referral.objects.select_related("patient", "from_doctor", "to_doctor", "to_department").all()
    serializer_class = ReferralSerializer
    permission_classes = [HasPermission]
    code = "consultations.refer"
    filterset_fields = ["status", "patient", "from_doctor", "to_doctor", "to_department"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        referral = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "clinical.referral",
                  record=str(referral.patient), object_id=referral.id, request=self.request)
