from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.radiology.models import RadiologyReport, RadiologyRequest
from apps.radiology.serializers import RadiologyReportSerializer, RadiologyRequestSerializer


class RadiologyRequestViewSet(viewsets.ModelViewSet):
    queryset = RadiologyRequest.objects.select_related("patient", "doctor").all()
    serializer_class = RadiologyRequestSerializer
    permission_classes = [HasPermission]
    code = "radiology.view"
    write_code = "radiology.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "procedure_type", "patient", "doctor"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number", "body_part"]
    ordering_fields = ["requested_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("doctor"):
            return qs.filter(doctor=user)
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        imaging_request = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "radiology.request",
                  record=str(imaging_request.patient), object_id=imaging_request.id,
                  request=self.request, new_value=serializer.data)

    def _transition(self, request, imaging_request, new_status, description):
        previous = {"status": imaging_request.status}
        imaging_request.status = new_status
        if new_status in (RadiologyRequest.STATUS_COMPLETED, RadiologyRequest.STATUS_REVIEWED):
            imaging_request.completed_at = timezone.now()
        imaging_request.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "radiology.request",
                  record=str(imaging_request.patient), object_id=imaging_request.id,
                  request=request, previous_value=previous, new_value={"status": new_status},
                  description=description)
        return Response(RadiologyRequestSerializer(imaging_request).data)

    @action(detail=True, methods=["post"])
    def queue(self, request, pk=None):
        imaging_request = self.get_object()
        return self._transition(request, imaging_request, RadiologyRequest.STATUS_QUEUED, "queued")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        imaging_request = self.get_object()
        return self._transition(request, imaging_request, RadiologyRequest.STATUS_IN_PROGRESS, "examination started")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        imaging_request = self.get_object()
        if not hasattr(imaging_request, "report"):
            return Response({"detail": "Attach a radiology report before completing."}, status=400)
        return self._transition(request, imaging_request, RadiologyRequest.STATUS_COMPLETED, "examination completed")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        imaging_request = self.get_object()
        return self._transition(request, imaging_request, RadiologyRequest.STATUS_CANCELLED, "cancelled")


class RadiologyReportViewSet(viewsets.ModelViewSet):
    queryset = RadiologyReport.objects.select_related("request").all()
    serializer_class = RadiologyReportSerializer
    permission_classes = [HasPermission]
    code = "radiology.view"
    write_code = "radiology.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["request"]

    def perform_create(self, serializer):
        report = serializer.save(radiologist=self.request.user, created_by=self.request.user)
        imaging_request = report.request
        imaging_request.status = RadiologyRequest.STATUS_COMPLETED
        imaging_request.completed_at = timezone.now()
        imaging_request.save()
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "radiology.report",
                  record=str(imaging_request.patient), object_id=report.id,
                  request=self.request, description=f"report for {imaging_request.get_procedure_type_display()}")
        if imaging_request.doctor:
            from apps.core.services import notify

            notify(imaging_request.doctor, "Imaging report ready",
                   f"Report ready for {imaging_request.patient.full_name} "
                   f"({imaging_request.get_procedure_type_display()}).",
                   notification_type="lab_result", link="/radiology")
