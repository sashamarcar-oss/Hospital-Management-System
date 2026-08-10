from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.laboratory.models import LabRequest, LabRequestItem, LabResult, LabTestCatalog
from apps.patients.serializers import PatientSummarySerializer


class LabTestCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestCatalog
        fields = ["id", "name", "category", "price", "sample_type", "normal_range",
                  "units", "description", "is_active"]


class LabResultSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source="technician.get_full_name", read_only=True)
    test_name = serializers.CharField(source="request_item.test.name", read_only=True)
    test_category = serializers.CharField(source="request_item.test.category", read_only=True)
    sample_type = serializers.CharField(source="request_item.test.sample_type", read_only=True)

    class Meta:
        model = LabResult
        fields = [
            "id", "request_item", "test_name", "test_category", "sample_type", "result",
            "units", "reference_range", "comments", "technician", "technician_name",
            "report_file", "is_abnormal", "completed_at",
        ]
        read_only_fields = ["technician", "completed_at"]

    def create(self, validated_data):
        result = LabResult.objects.create(**validated_data)
        item = validated_data["request_item"]
        if result.report_file:
            item.status = LabRequestItem.STATUS_COMPLETED
            item.save(update_fields=["status"])
        return result


class LabRequestItemSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source="test.name", read_only=True)
    normal_range = serializers.CharField(source="test.normal_range", read_only=True)
    units = serializers.CharField(source="test.units", read_only=True)
    price = serializers.DecimalField(source="test.price", read_only=True, max_digits=12, decimal_places=2)
    result = LabResultSerializer(read_only=True)

    class Meta:
        model = LabRequestItem
        fields = ["id", "test", "test_name", "normal_range", "units", "price", "status", "result"]


class LabRequestSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    items = LabRequestItemSerializer(many=True, read_only=True)
    test_ids = serializers.ListField(write_only=True, required=False, child=serializers.IntegerField())
    test_count = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)

    class Meta:
        model = LabRequest
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "consultation",
            "priority", "status", "clinical_notes", "requested_at", "completed_at",
            "items", "test_ids", "test_count", "total_price",
        ]
        read_only_fields = ["requested_at", "completed_at", "status"]

    def create(self, validated_data):
        test_ids = validated_data.pop("test_ids", [])
        if not test_ids:
            from rest_framework import exceptions

            raise exceptions.ValidationError({"test_ids": "At least one test is required."})
        lab_request = LabRequest.objects.create(**validated_data)
        for test_id in test_ids:
            LabRequestItem.objects.create(lab_request=lab_request, test_id=test_id)
        return lab_request


class LabResultCreateSerializer(serializers.Serializer):
    """Enter results for one or more request items in a single call."""

    results = LabResultSerializer(many=True)
