from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.emergency.models import EmergencyVisit
from apps.emergency.serializers import EmergencyVisitSerializer


class EmergencyVisitViewSet(viewsets.ModelViewSet):
    queryset = EmergencyVisit.objects.select_related("patient", "assigned_doctor", "triaged_by").all()
    serializer_class = EmergencyVisitSerializer
    permission_classes = [HasPermission]
    code = "emergency.view"
    write_code = "emergency.update"
    filterset_fields = ["status", "priority", "patient", "assigned_doctor", "mode_of_arrival"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__patient_number",
                     "chief_complaint"]
    ordering_fields = ["arrival_time", "priority"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        visit = serializer.save(triaged_by=self.request.user, created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "emergency.visit",
                  record=str(visit.patient), object_id=visit.id, request=self.request,
                  description=f"emergency {visit.get_priority_display()}")

    def _transition(self, request, visit, new_status, description, extra=None):
        previous = {"status": visit.status}
        for attr, value in (extra or {}).items():
            setattr(visit, attr, value)
        if new_status in (EmergencyVisit.STATUS_ADMITTED, EmergencyVisit.STATUS_REFERRED,
                          EmergencyVisit.STATUS_DISCHARGED):
            visit.completed_at = timezone.now()
        visit.status = new_status
        visit.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "emergency.visit",
                  record=str(visit.patient), object_id=visit.id, request=request,
                  previous_value=previous, new_value={"status": new_status},
                  description=description)
        return Response(EmergencyVisitSerializer(visit).data)

    @action(detail=True, methods=["post"])
    def assign_doctor(self, request, pk=None):
        if not request.user.has_permission_code("emergency.assign"):
            raise PermissionDenied("You do not have permission to assign emergency doctors.")
        visit = self.get_object()
        return self._transition(request, visit, visit.status, "doctor assigned",
                                extra={"assigned_doctor_id": request.data.get("doctor")})

    @action(detail=True, methods=["post"])
    def start_treatment(self, request, pk=None):
        visit = self.get_object()
        return self._transition(request, visit, EmergencyVisit.STATUS_IN_TREATMENT, "treatment started")

    @action(detail=True, methods=["post"])
    def admit(self, request, pk=None):
        visit = self.get_object()
        return self._transition(request, visit, EmergencyVisit.STATUS_ADMITTED, "admitted to ward")

    @action(detail=True, methods=["post"])
    def refer(self, request, pk=None):
        visit = self.get_object()
        return self._transition(request, visit, EmergencyVisit.STATUS_REFERRED, "referred",
                                extra={"referral_notes": request.data.get("notes", "")})

    @action(detail=True, methods=["post"])
    def discharge(self, request, pk=None):
        visit = self.get_object()
        return self._transition(request, visit, EmergencyVisit.STATUS_DISCHARGED, "discharged",
                                extra={"treatment_notes": request.data.get("treatment_notes", "")})

    @action(detail=False, methods=["get"])
    def active(self, request):
        qs = self.get_queryset().filter(
            status__in=[EmergencyVisit.STATUS_TRIAGE, EmergencyVisit.STATUS_WAITING,
                        EmergencyVisit.STATUS_IN_TREATMENT]
        )
        return Response(EmergencyVisitSerializer(qs, many=True).data)
