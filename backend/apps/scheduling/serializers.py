from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import UserBriefSerializer
from apps.scheduling.models import NurseShift

class NurseShiftSerializer(serializers.ModelSerializer):
    nurse_details = UserBriefSerializer(source="nurse", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    effective_status = serializers.SerializerMethodField()
    class Meta:
        model = NurseShift
        fields = "__all__"
        read_only_fields = ["created_by", "created_at", "updated_at"]
    def get_effective_status(self, obj):
        # Cancellation and missed status are explicit operational decisions. All
        # other statuses are derived from the current time so they never stale.
        if obj.status in (NurseShift.STATUS_CANCELLED, NurseShift.STATUS_MISSED):
            return obj.status
        now = timezone.localtime()
        start = timezone.make_aware(datetime.combine(obj.shift_date, obj.start_time), timezone.get_current_timezone())
        end = timezone.make_aware(datetime.combine(obj.shift_date + timedelta(days=1 if obj.end_time <= obj.start_time else 0), obj.end_time), timezone.get_current_timezone())
        return NurseShift.STATUS_ACTIVE if start <= now < end else (NurseShift.STATUS_COMPLETED if now >= end else obj.status)
    def validate(self, attrs):
        nurse, day = attrs.get("nurse", getattr(self.instance, "nurse", None)), attrs.get("shift_date", getattr(self.instance, "shift_date", None))
        start, end = attrs.get("start_time", getattr(self.instance, "start_time", None)), attrs.get("end_time", getattr(self.instance, "end_time", None))
        if nurse and (not nurse.is_active or nurse.is_patient_account or nurse.in_roles("patient")):
            raise serializers.ValidationError({"nurse": "The selected user must be an active staff member."})
        if start == end: raise serializers.ValidationError({"end_time": "Shift start and end times cannot be the same."})
        if nurse and day and start and end:
            cs, ce = datetime.combine(day, start), datetime.combine(day + timedelta(days=1 if end <= start else 0), end)
            qs = NurseShift.objects.filter(nurse=nurse, shift_date__in=[day, day - timedelta(days=1)]).exclude(status=NurseShift.STATUS_CANCELLED)
            if self.instance: qs = qs.exclude(pk=self.instance.pk)
            for item in qs:
                es = datetime.combine(item.shift_date, item.start_time); ee = datetime.combine(item.shift_date + timedelta(days=1 if item.end_time <= item.start_time else 0), item.end_time)
                if cs < ee and es < ce: raise serializers.ValidationError({"non_field_errors": ["This nurse already has a shift scheduled during this time."]})
        return attrs
