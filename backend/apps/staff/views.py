from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role, User
from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.staff.models import Attendance, LeaveRequest, Shift, Staff
from apps.staff.serializers import (
    AttendanceSerializer,
    LeaveRequestSerializer,
    ShiftSerializer,
    StaffCreateSerializer,
    StaffSerializer,
)


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.select_related("user__department").all()
    serializer_class = StaffSerializer
    permission_classes = [HasPermission]
    code = "staff.view"
    write_code = "staff.update"
    search_fields = ["employee_id", "user__first_name", "user__last_name", "user__email", "user__phone", "job_title"]
    filterset_fields = ["employment_status", "user__department", "user__role"]
    ordering_fields = ["employee_id", "date_joined"]

    def get_serializer_class(self):
        if self.action == "create":
            return StaffCreateSerializer
        return StaffSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        data = dict(serializer.validated_data)
        role = Role.objects.filter(code=data.pop("role")).first()
        user = User.objects.create(
            username=data.pop("username"),
            email=data.pop("email"),
            first_name=data.pop("first_name"),
            last_name=data.pop("last_name"),
            phone=data.pop("phone", ""),
            role=role,
            department=data.pop("department", None),
        )
        user.set_password(data.pop("password"))
        user.save()
        staff = Staff.objects.create(user=user, **data)
        audit_log(
            self.request.user, AuditLog.ACTION_CREATE, "staff.staff",
            record=staff.employee_id, object_id=staff.id, request=self.request,
            new_value=serializer.data,
        )
        return staff

    def perform_update(self, serializer):
        staff = serializer.save()
        audit_log(
            self.request.user, AuditLog.ACTION_UPDATE, "staff.staff",
            record=staff.employee_id, object_id=staff.id, request=self.request,
            previous_value={"employment_status": staff.employment_status},
            new_value=serializer.data,
        )

    def perform_destroy(self, instance):
        audit_log(
            self.request.user, AuditLog.ACTION_DELETE, "staff.staff",
            record=instance.employee_id, object_id=instance.id, request=self.request,
        )
        instance.user.is_active = False
        instance.user.save(update_fields=["is_active"])
        instance.employment_status = Staff.STATUS_INACTIVE
        instance.save(update_fields=["employment_status"])

    @action(detail=False, methods=["get"])
    def birthdays(self, request):
        from django.db.models.functions import ExtractMonth, ExtractDay

        qs = (
            self.queryset.filter(user__date_joined__isnull=False)
            .annotate(month=ExtractMonth("user__date_joined"), day=ExtractDay("user__date_joined"))
            .order_by("month", "day")[:50]
        )
        return Response(StaffSerializer(qs, many=True).data)


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [HasPermission]
    code = "staff.view"
    write_code = "staff.update"
    pagination_class = None


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related("staff__user").all()
    serializer_class = AttendanceSerializer
    permission_classes = [HasPermission]
    code = "staff.view"
    write_code = "staff.manage_attendance"
    filterset_fields = ["staff", "date", "status"]
    search_fields = ["staff__employee_id", "staff__user__first_name", "staff__user__last_name"]
    ordering_fields = ["-date"]


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("staff__user").all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasPermission]
    code = "staff.view"
    write_code = "staff.manage_leave"
    filterset_fields = ["staff", "status", "leave_type"]
    search_fields = ["staff__employee_id", "staff__user__first_name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave = self.get_object()
        previous = {"status": leave.status}
        leave.status = LeaveRequest.STATUS_APPROVED
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()
        leave.staff.user.is_active = True
        leave.staff.save()
        audit_log(
            request.user, AuditLog.ACTION_UPDATE, "staff.leave",
            record=f"approved leave {leave.id}", object_id=leave.id, request=request,
            previous_value=previous, new_value={"status": leave.status},
        )
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave = self.get_object()
        previous = {"status": leave.status}
        leave.status = LeaveRequest.STATUS_REJECTED
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()
        audit_log(
            request.user, AuditLog.ACTION_UPDATE, "staff.leave",
            record=f"rejected leave {leave.id}", object_id=leave.id, request=request,
            previous_value=previous, new_value={"status": leave.status},
        )
        return Response(LeaveRequestSerializer(leave).data)
