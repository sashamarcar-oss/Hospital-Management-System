import io

from django.db.models import Q
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission, IsPatientAccountOwner
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer, PatientSummarySerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.select_related("user").all()
    serializer_class = PatientSerializer
    permission_classes = [HasPermission, IsPatientAccountOwner]
    code = "patients.view"
    write_code = "patients.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        "patient_number", "first_name", "middle_name", "last_name",
        "phone", "email", "national_id", "insurance_number",
    ]
    filterset_fields = ["gender", "blood_group", "is_active", "insurance_provider"]
    ordering_fields = ["first_name", "last_name", "created_at", "patient_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            if linked:
                return qs.filter(pk=linked.pk)
            return qs.none()
        return qs

    def _audit(self, request, action, patient, previous=None, new=None):
        audit_log(
            request.user, action, "patients.patient",
            record=patient.patient_number, object_id=patient.id, request=request,
            previous_value=previous, new_value=new,
        )

    def perform_create(self, serializer):
        patient = serializer.save(created_by=self.request.user)
        self._audit(self.request, AuditLog.ACTION_CREATE, patient, new=serializer.data)

    def perform_update(self, serializer):
        previous = {"full_name": serializer.instance.full_name}
        patient = serializer.save(updated_by=self.request.user)
        self._audit(self.request, AuditLog.ACTION_UPDATE, patient, previous=previous, new=serializer.data)

    def perform_destroy(self, instance):
        self._audit(self.request, AuditLog.ACTION_DELETE, instance)
        instance.soft_delete(self.request.user)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        patient = self.get_object()
        return Response(PatientSummarySerializer(patient).data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Fast global search: patient number, name, phone, national id, insurance number."""
        term = request.query_params.get("q", "").strip()
        limit = int(request.query_params.get("limit", 20))
        qs = self.get_queryset()
        if term:
            qs = qs.filter(
                Q(patient_number__icontains=term)
                | Q(first_name__icontains=term)
                | Q(middle_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(phone__icontains=term)
                | Q(national_id__icontains=term)
                | Q(insurance_number__icontains=term)
            )
        return Response(PatientSummarySerializer(qs[:limit], many=True).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Patients"
        headers = ["Patient Number", "First Name", "Middle Name", "Last Name", "Date of Birth",
                   "Gender", "Phone", "Email", "Blood Group", "Allergies", "Insurance Provider"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        qs = self.filter_queryset(self.get_queryset())
        for p in qs:
            ws.append([p.patient_number, p.first_name, p.middle_name, p.last_name,
                       str(p.date_of_birth), p.gender, p.phone, p.email,
                       p.blood_group, p.allergies, p.insurance_provider])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="patients.xlsx"'
        return response
