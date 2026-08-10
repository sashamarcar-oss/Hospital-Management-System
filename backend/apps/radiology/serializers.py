from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.patients.serializers import PatientSummarySerializer
from apps.radiology.models import RadiologyReport, RadiologyRequest


class RadiologyReportSerializer(serializers.ModelSerializer):
    radiologist_name = serializers.CharField(source="radiologist.get_full_name", read_only=True)

    class Meta:
        model = RadiologyReport
        fields = ["id", "request", "findings", "impression", "conclusion",
                  "radiologist", "radiologist_name", "report_file", "completed_at"]
        read_only_fields = ["radiologist", "completed_at"]


class RadiologyRequestSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    report = RadiologyReportSerializer(read_only=True)

    class Meta:
        model = RadiologyRequest
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "consultation",
            "procedure_type", "body_part", "clinical_indication", "priority", "status",
            "requested_at", "completed_at", "report",
        ]
        read_only_fields = ["requested_at", "completed_at", "status"]
