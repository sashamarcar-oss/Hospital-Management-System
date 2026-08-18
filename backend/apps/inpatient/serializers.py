from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.inpatient.models import (
    Admission,
    Bed,
    BedAssignment,
    Discharge,
    FluidBalance,
    ICUMonitoringRecord,
    ICUMonitoringSheet,
    ICUThreshold,
    NurseAssignment,
    NursingHandover,
    NursingNote,
    NursingNoteAmendment,
    Room,
    Ward,
)
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
    ward = serializers.IntegerField(source="room.ward_id", read_only=True)
    current_patient = PatientSummarySerializer(read_only=True)
    current_admission = serializers.SerializerMethodField()

    class Meta:
        model = Bed
        fields = ["id", "room", "room_name", "ward", "ward_name", "bed_number", "status",
                  "notes", "last_cleaned_at", "current_patient", "current_admission"]

    def get_current_admission(self, obj):
        admission = obj.current_admission
        if not admission:
            return None
        return {
            "id": admission.id,
            "admission_number": admission.admission_number,
            "patient": admission.patient_id,
            "doctor": admission.doctor_id,
            "doctor_name": admission.doctor.get_full_name() if admission.doctor else None,
            "assigned_nurse": admission.assigned_nurse_id,
            "assigned_nurse_name": admission.assigned_nurse.get_full_name() if admission.assigned_nurse else None,
            "admission_date": admission.admission_date,
            "diagnosis": admission.diagnosis,
            "status": admission.status,
        }


class BedAssignmentSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    bed_number = serializers.CharField(source="bed.bed_number", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.get_full_name", read_only=True)
    released_by_name = serializers.CharField(source="released_by.get_full_name", read_only=True)

    class Meta:
        model = BedAssignment
        fields = [
            "id", "admission", "admission_number", "patient_details", "bed", "bed_number",
            "ward", "ward_name", "room", "room_number", "assigned_at",
            "expected_discharge_date", "released_at", "assigned_by", "assigned_by_name",
            "released_by", "released_by_name", "release_reason", "notes", "status", "is_active",
        ]
        read_only_fields = ["assigned_by", "assigned_by_name", "released_by", "released_by_name"]


class TransferSerializer(serializers.ModelSerializer):
    """Bed assignments that represent patient transfers (read only)."""

    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    from_bed = serializers.CharField(source="bed.bed_number", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.get_full_name", read_only=True)

    class Meta:
        model = BedAssignment
        fields = ["id", "admission", "patient_details", "from_bed", "ward", "ward_name",
                  "assigned_at", "assigned_by", "assigned_by_name", "released_at", "release_reason"]


class AdmissionSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    assigned_nurse_details = UserBriefSerializer(source="assigned_nurse", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    room_name = serializers.SerializerMethodField()
    bed_name = serializers.SerializerMethodField()
    active_bed_assignment = BedAssignmentSerializer(read_only=True)

    class Meta:
        model = Admission
        fields = [
            "id", "admission_number", "patient", "patient_details", "doctor", "doctor_details",
            "assigned_nurse", "assigned_nurse_details", "department", "department_name", "ward",
            "ward_name", "room", "room_name", "bed", "bed_name", "admission_date",
            "admission_reason", "diagnosis", "notes", "expected_discharge_date", "status",
            "discharged_at", "active_bed_assignment",
        ]
        read_only_fields = ["discharged_at", "admission_number"]

    def get_room_name(self, obj):
        return f"{obj.room.room_number}" if obj.room else None

    def get_bed_name(self, obj):
        return f"{obj.bed.bed_number}" if obj.bed else None

    def validate(self, attrs):
        bed = attrs.get("bed")
        if bed and bed.status not in (Bed.STATUS_AVAILABLE, Bed.STATUS_RESERVED):
            raise serializers.ValidationError({"bed": "Only an available bed can be assigned."})
        return attrs


class NurseAssignmentSerializer(serializers.ModelSerializer):
    nurse_details = UserBriefSerializer(source="nurse", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.get_full_name", read_only=True)

    class Meta:
        model = NurseAssignment
        fields = ["id", "admission", "nurse", "nurse_details", "assigned_by", "assigned_by_name",
                  "role", "assigned_at", "unassigned_at", "notes"]
        read_only_fields = ["assigned_by", "assigned_at", "unassigned_at"]


class NursingNoteSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    bed_name = serializers.SerializerMethodField()
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    amendments = serializers.SerializerMethodField()

    class Meta:
        model = NursingNote
        fields = [
            "id", "admission", "admission_number", "patient_details", "nurse", "nurse_name",
            "ward", "ward_name", "bed", "bed_name", "shift_type", "shift", "note_date",
            "start_time", "end_time", "note", "status", "submitted_at", "amended_from",
            "amendment_reason", "condition", "consciousness", "pain_assessment", "pain_score",
            "mobility", "nutrition_intake", "fluid_intake_ml", "fluid_output_ml",
            "medication_observations", "wound_dressing_observations", "patient_complaints",
            "interventions", "patient_response", "safety_concerns", "fall_risk",
            "doctor_instructions", "observations", "pending_tasks",
            "handover_current_condition", "handover_recent_changes",
            "handover_interventions_provided", "handover_pending_tasks",
            "handover_important_observations", "handover_follow_up_required",
            "recorded_at", "amendments",
        ]
        read_only_fields = [
            "nurse", "nurse_name", "submitted_at", "amended_from", "amendment_reason",
            "recorded_at", "amendments",
        ]

    def get_bed_name(self, obj):
        return obj.bed.bed_number if obj.bed else None

    def get_amendments(self, obj):
        if not obj.amendments.exists():
            return []
        return NursingNoteAmendmentSerializer(obj.amendments.all(), many=True).data


class NursingNoteAmendmentSerializer(serializers.ModelSerializer):
    amended_by_name = serializers.CharField(source="amended_by.get_full_name", read_only=True)

    class Meta:
        model = NursingNoteAmendment
        fields = ["id", "note", "amended_by", "amended_by_name", "amended_at", "reason",
                  "changed_fields", "previous_snapshot"]
        read_only_fields = ["amended_by", "amended_at"]


class NursingHandoverSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)
    incoming_nurse_details = UserBriefSerializer(source="incoming_nurse", read_only=True)
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    ward_name = serializers.CharField(source="ward.name", read_only=True)
    bed_name = serializers.SerializerMethodField()

    class Meta:
        model = NursingHandover
        fields = [
            "id", "admission", "admission_number", "patient_details", "ward", "ward_name",
            "bed", "bed_name", "nurse", "nurse_name", "incoming_nurse", "incoming_nurse_details",
            "shift", "shift_type", "handover_date", "condition", "current_condition",
            "recent_changes", "interventions_provided", "pending_tasks",
            "important_observations", "follow_up_required", "medication_due",
            "pending_investigations", "precautions", "observations", "recorded_at",
        ]
        read_only_fields = ["nurse", "nurse_name", "recorded_at"]

    def get_bed_name(self, obj):
        return obj.bed.bed_number if obj.bed else None


class ICUMonitoringSheetSerializer(serializers.ModelSerializer):
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    bed_name = serializers.CharField(source="bed.bed_number", read_only=True)
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    record_count = serializers.IntegerField(source="records.count", read_only=True)

    class Meta:
        model = ICUMonitoringSheet
        fields = ["id", "admission", "admission_number", "patient_details", "bed", "bed_name",
                  "nurse", "nurse_name", "doctor", "doctor_name", "monitoring_date", "period",
                  "interval", "status", "notes", "record_count", "created_at"]
        read_only_fields = ["created_at"]


class ICUMonitoringRecordSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    gcs_total = serializers.IntegerField(read_only=True)
    total_intake_ml = serializers.IntegerField(read_only=True)
    total_output_ml = serializers.IntegerField(read_only=True)
    net_balance_ml = serializers.IntegerField(read_only=True)
    alerts = serializers.SerializerMethodField()

    class Meta:
        model = ICUMonitoringRecord
        fields = "__all__"
        read_only_fields = ["nurse", "nurse_name", "created_by", "updated_by", "gcs_total",
                            "total_intake_ml", "total_output_ml", "net_balance_ml", "alerts"]

    def get_alerts(self, obj):
        from apps.inpatient.services import evaluate_icu_record_alerts

        return evaluate_icu_record_alerts(obj)


class FluidBalanceSerializer(serializers.ModelSerializer):
    nurse_name = serializers.CharField(source="nurse.get_full_name", read_only=True)
    admission_number = serializers.CharField(source="admission.admission_number", read_only=True)
    patient_details = PatientSummarySerializer(source="admission.patient", read_only=True)
    total_intake_ml = serializers.IntegerField(read_only=True)
    total_output_ml = serializers.IntegerField(read_only=True)
    net_balance_ml = serializers.IntegerField(read_only=True)

    class Meta:
        model = FluidBalance
        fields = ["id", "admission", "admission_number", "patient_details", "nurse", "nurse_name",
                  "balance_date", "period", "oral_intake_ml", "iv_intake_ml", "urine_output_ml",
                  "drain_output_ml", "other_output_ml", "total_intake_ml", "total_output_ml",
                  "net_balance_ml", "notes", "created_at"]
        read_only_fields = ["nurse", "nurse_name", "created_at"]


class ICUThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICUThreshold
        fields = ["id", "parameter", "name", "unit", "min_alert", "max_alert",
                  "min_critical", "max_critical", "is_active", "description"]


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
            "admission_number": obj.admission.admission_number,
            "ward": obj.admission.ward.name if obj.admission.ward else None,
            "admitted_on": obj.admission.admission_date,
            "diagnosis": obj.admission.diagnosis,
        }


class InpatientStatsSerializer(serializers.Serializer):
    total_beds = serializers.IntegerField()
    available_beds = serializers.IntegerField()
    occupied_beds = serializers.IntegerField()
    reserved_beds = serializers.IntegerField()
    admitted_patients = serializers.IntegerField()
    active_icu_patients = serializers.IntegerField()
    pending_handovers = serializers.IntegerField()
    recent_vitals_count = serializers.IntegerField()
    my_assigned_patients = serializers.IntegerField(required=False)
    my_current_shift = serializers.CharField(required=False, allow_null=True)
    pending_vitals = serializers.IntegerField(required=False)
    my_inpatients = serializers.IntegerField(required=False)
    patients_requiring_review = serializers.IntegerField(required=False)
    pending_results = serializers.IntegerField(required=False)
    patients_requiring_attention = serializers.IntegerField(required=False)
