from datetime import date, timedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.models import Role
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify
from apps.scheduling.models import NurseShift
from apps.scheduling.serializers import NurseShiftSerializer

class NurseShiftViewSet(viewsets.ModelViewSet):
    serializer_class = NurseShiftSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["nurse", "department", "shift_type", "status", "shift_date"]
    search_fields = ["nurse__first_name", "nurse__last_name", "nurse__username", "location"]
    ordering_fields = ["shift_date", "start_time", "status"]
    def is_manager(self): return self.request.user.in_roles(Role.CODE_ADMIN, Role.CODE_SUPER_ADMIN, Role.CODE_HR) or self.request.user.is_superuser
    def get_queryset(self):
        qs = NurseShift.objects.select_related("nurse__department", "department", "created_by")
        return qs if self.is_manager() else qs.filter(nurse=self.request.user)
    def create(self, request, *args, **kwargs):
        if not self.is_manager(): return Response({"detail": "Only shift managers can create shifts."}, status=403)
        return super().create(request, *args, **kwargs)
    def update(self, request, *args, **kwargs):
        if not self.is_manager(): return Response({"detail": "Only shift managers can update shifts."}, status=403)
        return super().update(request, *args, **kwargs)
    def destroy(self, request, *args, **kwargs):
        if not self.is_manager(): return Response({"detail": "Only shift managers can cancel shifts."}, status=403)
        return super().destroy(request, *args, **kwargs)
    def perform_create(self, serializer):
        shift = serializer.save(created_by=self.request.user); notify(shift.nurse, "New shift assigned", f"You have been assigned a {shift.get_shift_type_display()} shift on {shift.shift_date}.", link="/my-shifts"); audit_log(self.request.user, AuditLog.ACTION_CREATE, "shifts.nurse_shift", record=str(shift.id), object_id=shift.id, request=self.request)
    def perform_update(self, serializer):
        shift = serializer.save(); notify(shift.nurse, "Shift updated", f"Your shift on {shift.shift_date} has been updated.", link="/my-shifts")
    def perform_destroy(self, instance):
        instance.status = NurseShift.STATUS_CANCELLED; instance.save(update_fields=["status", "updated_at"]); notify(instance.nurse, "Shift cancelled", f"Your shift on {instance.shift_date} was cancelled.", link="/my-shifts")
    @action(detail=False, methods=["get"], url_path="my-shifts")
    def my_shifts(self, request): return Response(NurseShiftSerializer(NurseShift.objects.filter(nurse=request.user), many=True).data)
    @action(detail=False, methods=["get"])
    def upcoming(self, request): return Response(NurseShiftSerializer(self.get_queryset().filter(shift_date__gte=date.today()).exclude(status=NurseShift.STATUS_CANCELLED)[:20], many=True).data)
    @action(detail=False, methods=["get"])
    def calendar(self, request):
        start = date.fromisoformat(request.query_params.get("start", str(date.today()))); end = date.fromisoformat(request.query_params.get("end", str(start + timedelta(days=31))))
        return Response(NurseShiftSerializer(self.get_queryset().filter(shift_date__range=[start, end]), many=True).data)
