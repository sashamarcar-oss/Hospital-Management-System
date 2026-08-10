from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserBriefSerializer
from apps.departments.models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, required=False)
    staff_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "description", "is_active", "member_count", "staff_count", "created_at"]

    def validate_name(self, value):
        qs = Department.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A department with this name already exists.")
        return value


class DepartmentWithStaffSerializer(DepartmentSerializer):
    members = UserBriefSerializer(many=True, read_only=True)
    staff = UserBriefSerializer(many=True, read_only=True)

    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + ["members", "staff"]
