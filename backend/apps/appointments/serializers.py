from rest_framework import serializers

from apps.appointments.models import Appointment, Queue
from apps.patients.serializers import PatientSummarySerializer
from apps.accounts.serializers import UserBriefSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    display_time = serializers.CharField(read_only=True)
    queue_entry = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "department",
            "department_name", "appointment_date", "start_time", "end_time", "reason",
            "priority", "status", "notes", "display_time", "queue_entry", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        if attrs.get("end_time") and attrs.get("start_time") and attrs.get("end_time") <= attrs.get("start_time"):
            raise serializers.ValidationError({"end_time": "End time must be after start time."})

        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        department = attrs.get("department", getattr(self.instance, "department", None))

        if doctor and not doctor.is_active:
            raise serializers.ValidationError({"doctor": "Select an active doctor."})

        if (
            doctor
            and doctor.role
            and doctor.role.code == "doctor"
            and doctor.department_id
            and department
            and doctor.department_id != department.id
        ):
            raise serializers.ValidationError(
                {"doctor": "Select a doctor assigned to the selected department."}
            )
        return attrs

    def get_queue_entry(self, obj):
        queue = obj.queue_entries.filter(status__in=[Queue.STATUS_WAITING, Queue.STATUS_IN_CONSULTATION]).first()
        if queue:
            return {"id": queue.id, "queue_number": queue.queue_number, "status": queue.status}
        return None


class QueueSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    waiting_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Queue
        fields = [
            "id", "patient", "patient_details", "appointment", "department", "department_name",
            "doctor", "doctor_name", "queue_number", "status", "priority", "checked_in_at",
            "called_at", "completed_at", "waiting_minutes",
        ]
        read_only_fields = ["queue_number", "checked_in_at", "called_at", "completed_at"]
