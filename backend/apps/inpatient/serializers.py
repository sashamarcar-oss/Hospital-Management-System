from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.inpatient.models import Admission, Bed, Discharge, NursingNote, Room, Ward
from apps.patients.serializers import PatientSummarySerializer


class WardSerializer(serializers.ModelSerializer):
    bed_count = serializers.IntegerField(read_only=True)
    available_beds = serializers.IntegerField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Ward
        fields = ["id", "name", "code", "ward_type", "department", "department_name",
                  "is_active", "bed_count", "available_beds"]


class RoomSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source="ward.name", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "ward", "ward_name", "room_number", "room_type"]


class BedSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.__str__", read_only=True)
    ward_name = serializers.CharField(source="room.ward.name", read_only=True)
    current_patient = PatientSummarySerializer(read_only=True)

    class Meta:
        model = Bed
        fields = ["id", "room", "room_name", "ward_name", "bed_number", "status", "current_patient"]


class AdmissionSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    room_name = serializers.SerializerMethodField()
    bed_name = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "department",
            "department_name", "ward", "ward_name", "room", "room_name", "bed", "bed_name",
            "admission_date", "admission_reason", "diagnosis", "notes", "status",
            "discharged_at",
        ]
        read_only_fields = ["discharged_at"]

    def get_room_name(self, obj):
        return f"{obj.room.room_number}" if obj.room else None

    def get_bed_name(self, obj):
        return f"{obj.bed.bed_number}" if obj.bed else None

    def validate(self, attrs):
        bed = attrs.get("bed")
        if bed and bed.status == Bed.STATUS_MAINTENANCE:
            raise serializers.ValidationError({"bed": "Cannot assign a bed under maintenance."})
        return attrs


class NursingNoteSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)

    class Meta:
        model = NursingNote
        fields = ["id", "admission", "nurse", "nurse_name", "note", "shift", "recorded_at"]
        read_only_fields = ["nurse", "recorded_at"]


class DischargeSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    admission_details = serializers.SerializerMethodField()
    discharged_by_name = serializers.CharField(source="discharged_by.get_full_name", read_only=True)

    class Meta:
        model = Discharge
        fields = [
            "id", "admission", "admission_details", "patient", "patient_details",
            "discharge_date", "discharge_type", "diagnosis_summary", "treatment_summary",
            "medication", "outstanding_bills", "follow_up_instructions", "follow_up_date",
            "doctor_notes", "discharged_by", "discharged_by_name",
        ]
        read_only_fields = ["discharged_by", "discharge_date"]

    def get_admission_details(self, obj):
        return {
            "ward": obj.admission.ward.name if obj.admission.ward else None,
            "admitted_on": obj.admission.admission_date,
            "diagnosis": obj.admission.diagnosis,
        }
