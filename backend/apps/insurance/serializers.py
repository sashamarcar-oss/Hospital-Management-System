from rest_framework import serializers

from apps.insurance.models import InsuranceClaim, InsurancePolicy, InsuranceProvider
from apps.patients.serializers import PatientSummarySerializer


class InsuranceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceProvider
        fields = ["id", "name", "code", "phone", "email", "address", "is_active"]


class InsurancePolicySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    patient_details = PatientSummarySerializer(source="patient", read_only=True)

    class Meta:
        model = InsurancePolicy
        fields = [
            "id", "patient", "patient_details", "provider", "provider_name",
            "policy_number", "membership_number", "coverage_type", "coverage_limit",
            "start_date", "end_date", "status",
        ]

    def validate(self, attrs):
        if attrs.get("end_date") and attrs.get("start_date") and attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs


class InsuranceClaimSerializer(serializers.ModelSerializer):
    policy_details = serializers.SerializerMethodField()
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)

    class Meta:
        model = InsuranceClaim
        fields = [
            "id", "policy", "policy_details", "patient", "patient_details", "invoice",
            "invoice_number", "claim_number", "amount", "status", "approved_amount",
            "rejected_amount", "patient_contribution", "submitted_date", "approval_date",
            "notes", "created_at",
        ]
        read_only_fields = ["claim_number", "created_at"]

    def get_policy_details(self, obj):
        return {
            "provider": obj.policy.provider.name,
            "policy_number": obj.policy.policy_number,
            "coverage_type": obj.policy.coverage_type,
        }
