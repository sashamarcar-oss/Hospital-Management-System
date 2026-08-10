from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.departments.models import Department
from apps.staff.models import Attendance, LeaveRequest, Shift, Staff


class StaffSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id", "user", "user_details", "employee_id", "job_title", "license_number",
            "qualifications", "date_joined", "employment_status", "salary", "address",
            "department",
        ]

    def get_user_details(self, obj):
        return UserBriefSerializer(obj.user).data

    def get_department(self, obj):
        return obj.user.department.name if obj.user.department else None


class StaffCreateSerializer(serializers.Serializer):
    """Create a staff member along with their user account."""

    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField()
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    password = serializers.CharField(write_only=True, min_length=8)
    employee_id = serializers.CharField()
    job_title = serializers.CharField(required=False, allow_blank=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    qualifications = serializers.CharField(required=False, allow_blank=True)
    date_joined = serializers.DateField()
    salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"


class AttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.display_name", read_only=True)
    employee_id = serializers.CharField(source="staff.employee_id", read_only=True)

    class Meta:
        model = Attendance
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.display_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ["approved_by", "approved_at", "status"]
