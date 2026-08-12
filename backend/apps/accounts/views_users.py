from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Permission, Role, User
from apps.accounts.permissions import HasPermission
from apps.accounts.serializers import (
    PermissionSerializer,
    RoleSerializer,
    UserBriefSerializer,
    UserSerializer,
)
from apps.core.models import AuditLog
from apps.core.services import audit_log


class UserViewSet(viewsets.ModelViewSet):
    """Manage users, assign roles, activate/deactivate accounts."""

    queryset = User.objects.select_related("role").all()
    serializer_class = UserSerializer
    permission_classes = [HasPermission]
    code = "settings.manage_users"
    search_fields = ["username", "first_name", "last_name", "email", "phone"]
    filterset_fields = ["role", "is_active", "department"]
    ordering_fields = ["username", "date_joined", "first_name"]

    def _audit(self, request, action, user, previous=None, new=None):
        audit_log(
            request.user,
            action,
            "accounts.user",
            record=user.username,
            object_id=user.id,
            request=request,
            previous_value=previous,
            new_value=new,
        )

    def get_permissions(self):
        if self.action == "doctors":
            return [HasPermission()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def doctors(self, request):
        """Brief list of doctors, optionally filtered by department (for booking forms)."""
        qs = self.queryset.filter(
            role__code="doctor",
            is_active=True,
        ).select_related("role", "department")
        department = request.query_params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        return Response(
            UserBriefSerializer(qs.order_by("first_name", "last_name"), many=True).data
        )

    def perform_create(self, serializer):
        user = serializer.save()
        user.created_by = self.request.user
        user.save()
        self._audit(self.request, AuditLog.ACTION_CREATE, user, new=serializer.data)

    def perform_update(self, serializer):
        previous = {
            "role": serializer.instance.role_name,
            "is_active": serializer.instance.is_active,
        }
        user = serializer.save()
        user.updated_by = self.request.user
        user.save()
        self._audit(
            self.request, AuditLog.ACTION_UPDATE, user, previous=previous, new=serializer.data
        )

    def perform_destroy(self, instance):
        previous = {"is_active": instance.is_active}
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        self._audit(self.request, AuditLog.ACTION_DELETE, instance, previous=previous)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        previous = {"is_active": user.is_active}
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        audit_log(
            request.user,
            AuditLog.ACTION_PERMISSION_CHANGE,
            "accounts.user",
            record=f"toggle_active {user.username}",
            object_id=user.id,
            request=request,
            previous_value=previous,
            new_value={"is_active": user.is_active},
        )
        return Response(UserSerializer(user).data)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_classes = [HasPermission]
    code = "settings.manage_permissions"
    pagination_class = None


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasPermission]
    code = "settings.manage_permissions"
    filterset_fields = ["module"]
    pagination_class = None


class MyPermissionsView(viewsets.ViewSet):
    """Return the permission codes for the currently authenticated user."""

    def list(self, request):
        user = request.user
        codes = UserSerializer(user).data.get("permission_codes", [])
        return Response({"role": user.role_code, "permissions": codes})
