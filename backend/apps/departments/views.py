from django.db.models import Count
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission
from apps.departments.models import Department
from apps.departments.serializers import DepartmentSerializer
from apps.core.models import AuditLog
from apps.core.services import audit_log


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.annotate(member_count=Count("members", distinct=True))
    serializer_class = DepartmentSerializer
    permission_classes = [HasPermission]
    code = "departments.view"
    write_code = "departments.update"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        dept = serializer.save()
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "departments.department",
                  record=dept.name, object_id=dept.id, request=self.request, new_value=serializer.data)

    def perform_update(self, serializer):
        previous = {"name": serializer.instance.name}
        dept = serializer.save()
        audit_log(self.request.user, AuditLog.ACTION_UPDATE, "departments.department",
                  record=dept.name, object_id=dept.id, request=self.request,
                  previous_value=previous, new_value=serializer.data)

    def perform_destroy(self, instance):
        audit_log(self.request.user, AuditLog.ACTION_DELETE, "departments.department",
                  record=instance.name, object_id=instance.id, request=self.request)
        instance.is_active = False
        instance.save(update_fields=["is_active"])
