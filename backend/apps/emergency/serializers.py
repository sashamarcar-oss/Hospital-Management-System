from rest_framework import serializers

from apps.emergency.models import EmergencyVisit
from apps.patients.serializers import PatientSummarySerializer
from apps.accounts.serializers import UserBriefSerializer


class EmergencyVisitSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    assigned_doctor_details = UserBriefSerializer(source="assigned_doctor", read_only=True)
    triaged_by_name = serializers.CharField(source="triaged_by.get_full_name", read_only=True)
    waiting_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = EmergencyVisit
        fields = [
            "id", "patient", "patient_details", "arrival_time", "mode_of_arrival",
            "priority", "chief_complaint", "triage_notes", "triage_score",
            "vitals_summary", "assigned_doctor", "assigned_doctor_details", "status",
            "treatment_notes", "referral_notes", "triaged_by", "triaged_by_name",
            "completed_at", "waiting_minutes",
        ]
        read_only_fields = ["triaged_by", "completed_at"]
