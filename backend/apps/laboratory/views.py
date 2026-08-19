from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.laboratory.models import LabRequest, LabRequestItem, LabResult, LabTestCatalog
from apps.laboratory.serializers import (
    LabRequestSerializer,
    LabResultSerializer,
    LabTestCatalogSerializer,
)


class LabTestCatalogViewSet(viewsets.ModelViewSet):
    queryset = LabTestCatalog.objects.all()
    serializer_class = LabTestCatalogSerializer
    permission_classes = [HasPermission]
    code = "laboratory.view"
    write_code = "laboratory.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "category", "sample_type"]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["name", "price"]


class LabRequestViewSet(viewsets.ModelViewSet):
    queryset = LabRequest.objects.select_related("patient", "doctor", "consultation").all()
    serializer_class = LabRequestSerializer
    permission_classes = [HasPermission]
    code = "laboratory.view"
    write_code = "laboratory.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "patient", "doctor", "consultation"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number"]
    ordering_fields = ["requested_at", "priority"]

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
        lab_request = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "laboratory.labrequest",
                  record=str(lab_request.patient), object_id=lab_request.id,
                  request=self.request, new_value=serializer.data)

    def perform_destroy(self, instance):
        audit_log(self.request.user, AuditLog.ACTION_DELETE, "laboratory.labrequest",
                  record=str(instance.patient), object_id=instance.id, request=self.request)
        instance.soft_delete(self.request.user)

    def _transition(self, request, lab_request, new_status, description, item_status=None):
        previous = {"status": lab_request.status}
        lab_request.status = new_status
        if new_status in (LabRequest.STATUS_COMPLETED, LabRequest.STATUS_REVIEWED):
            lab_request.completed_at = timezone.now()
        lab_request.save()
        if item_status:
            lab_request.items.update(status=item_status)
        audit_log(request.user, AuditLog.ACTION_UPDATE, "laboratory.labrequest",
                  record=str(lab_request.patient), object_id=lab_request.id,
                  request=request, previous_value=previous, new_value={"status": new_status},
                  description=description)
        return Response(LabRequestSerializer(lab_request).data)

    @action(detail=True, methods=["post"])
    def collect_sample(self, request, pk=None):
        lab_request = self.get_object()
        return self._transition(request, lab_request, LabRequest.STATUS_SAMPLE_COLLECTED,
                                "sample collected", LabRequestItem.STATUS_SAMPLE_COLLECTED)

    @action(detail=True, methods=["post"])
    def start_processing(self, request, pk=None):
        lab_request = self.get_object()
        return self._transition(request, lab_request, LabRequest.STATUS_PROCESSING,
                                "processing started", LabRequestItem.STATUS_PROCESSING)

    @action(detail=True, methods=["post"])
    def mark_completed(self, request, pk=None):
        lab_request = self.get_object()
        missing = lab_request.items.filter(result__isnull=True)
        if missing.exists():
            names = ", ".join(m.test.name for m in missing)
            return Response({"detail": f"Enter results for all tests before completing: {names}"},
                            status=400)
        return self._transition(request, lab_request, LabRequest.STATUS_COMPLETED,
                                "results completed", LabRequestItem.STATUS_COMPLETED)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        lab_request = self.get_object()
        return self._transition(request, lab_request, LabRequest.STATUS_REVIEWED,
                                "reviewed by doctor")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        lab_request = self.get_object()
        return self._transition(request, lab_request, LabRequest.STATUS_CANCELLED, "cancelled")

    @action(detail=False, methods=["get"])
    def pending(self, request):
        qs = self.get_queryset().filter(
            status__in=[LabRequest.STATUS_REQUESTED, LabRequest.STATUS_SAMPLE_COLLECTED,
                        LabRequest.STATUS_PROCESSING]
        ).order_by("requested_at")
        return Response(LabRequestSerializer(qs, many=True).data)


class LabResultViewSet(viewsets.ModelViewSet):
    queryset = LabResult.objects.select_related("request_item__test", "request_item__lab_request").all()
    serializer_class = LabResultSerializer
    permission_classes = [HasPermission]
    code = "laboratory.view"
    create_code = "laboratory.enter_results"
    write_code = "laboratory.enter_results"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["request_item", "is_abnormal"]
    search_fields = ["request_item__lab_request__patient__first_name",
                     "request_item__lab_request__patient__last_name"]
    ordering_fields = ["completed_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(request_item__lab_request__patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        result = serializer.save(technician=self.request.user, created_by=self.request.user)
        item = result.request_item
        item.status = LabRequestItem.STATUS_COMPLETED
        item.save(update_fields=["status"])
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "laboratory.labresult",
                  record=str(item.lab_request.patient), object_id=result.id,
                  request=self.request, description=f"result for {item.test.name}")

        if not item.lab_request.items.exclude(status=LabRequestItem.STATUS_COMPLETED).exists():
            item.lab_request.status = LabRequest.STATUS_COMPLETED
            item.lab_request.completed_at = timezone.now()
            item.lab_request.save()
            if item.lab_request.doctor:
                from apps.core.services import notify

                notify(item.lab_request.doctor, "Lab results ready",
                       f"Results are ready for {item.lab_request.patient.full_name}.",
                       notification_type="lab_result", link="/laboratory")
