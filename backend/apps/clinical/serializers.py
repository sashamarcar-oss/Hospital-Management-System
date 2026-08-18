from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.clinical.models import (
    Consultation,
    Diagnosis,
    Prescription,
    PrescriptionItem,
    Referral,
    VitalSigns,
)
from apps.patients.serializers import PatientSummarySerializer
from apps.pharmacy.models import Medicine


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ["id", "consultation", "icd_code", "name", "description", "is_primary"]


class NestedDiagnosisSerializer(serializers.ModelSerializer):
    """Writable diagnoses embedded in a consultation.

    ``consultation``/``patient`` are omitted here because the parent
    ConsultationSerializer resolves and assigns them when creating.
    """

    class Meta:
        model = Diagnosis
        fields = ["id", "icd_code", "name", "description", "is_primary"]
        read_only_fields = ["id"]


class VitalSignsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)

    class Meta:
        model = VitalSigns
        fields = [
            "id", "patient", "admission", "consultation", "temperature", "blood_pressure_systolic",
            "blood_pressure_diastolic", "pulse", "respiratory_rate", "oxygen_saturation",
            "weight", "height", "bmi", "pain_score", "blood_glucose", "notes", "recorded_by", "recorded_by_name",
            "recorded_at",
        ]
        read_only_fields = ["bmi", "recorded_by", "recorded_at"]

    def validate(self, attrs):
        if attrs.get("pain_score") is not None and not (0 <= attrs["pain_score"] <= 10):
            raise serializers.ValidationError({"pain_score": "Pain score must be between 0 and 10."})
        return attrs


class NestedVitalSignsSerializer(serializers.ModelSerializer):
    """Writable vital signs embedded in a consultation.

    ``patient``/``consultation``/``recorded_by`` are omitted here because the
    parent ConsultationSerializer resolves and assigns them when creating.
    """

    class Meta:
        model = VitalSigns
        fields = [
            "id", "temperature", "blood_pressure_systolic", "blood_pressure_diastolic",
            "pulse", "respiratory_rate", "oxygen_saturation", "weight", "height",
            "pain_score", "blood_glucose", "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs.get("pain_score") is not None and not (0 <= attrs["pain_score"] <= 10):
            raise serializers.ValidationError({"pain_score": "Pain score must be between 0 and 10."})
        return attrs


class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all())

    class Meta:
        model = PrescriptionItem
        fields = [
            "id", "prescription", "medicine", "medicine_name", "dosage", "frequency",
            "duration", "route", "quantity", "instructions", "dispensed_quantity",
        ]
        read_only_fields = ["dispensed_quantity"]


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    items = PrescriptionItemSerializer(many=True, required=False)
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Prescription
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "consultation",
            "status", "notes", "dispensed_by", "dispensed_at", "items", "item_count", "created_at",
        ]
        read_only_fields = ["dispensed_by", "dispensed_at", "created_at"]

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        prescription = Prescription.objects.create(**validated_data)
        for item in items:
            PrescriptionItem.objects.create(prescription=prescription, **item)
        return prescription

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items is not None:
            existing = {str(i.medicine_id): i for i in instance.items.all()}
            new_items = []
            for item in items:
                key = str(item.get("medicine").id)
                if key in existing:
                    for k, v in item.items():
                        setattr(existing[key], k, v)
                    existing[key].save()
                else:
                    new_items.append(item)
            for item in new_items:
                PrescriptionItem.objects.create(prescription=instance, **item)
        return instance


class ConsultationSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    doctor_details = UserBriefSerializer(source="doctor", read_only=True)
    diagnoses = NestedDiagnosisSerializer(many=True, required=False)
    vital_signs = NestedVitalSignsSerializer(many=True, required=False)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id", "patient", "patient_details", "doctor", "doctor_details", "appointment",
            "chief_complaint", "history_of_presenting_illness", "symptoms",
            "physical_examination", "clinical_notes", "treatment_plan", "procedures",
            "follow_up_date", "status", "recorded_at", "diagnoses", "vital_signs", "prescriptions",
        ]
        read_only_fields = ["recorded_at"]

    def create(self, validated_data):
        diagnoses = validated_data.pop("diagnoses", [])
        vitals = validated_data.pop("vital_signs", [])
        consultation = Consultation.objects.create(**validated_data)
        for d in diagnoses:
            Diagnosis.objects.create(consultation=consultation, patient=consultation.patient, **d)
        for v in vitals:
            VitalSigns.objects.create(consultation=consultation, patient=consultation.patient,
                                      recorded_by=self.context["request"].user, **v)
        return consultation

    def update(self, instance, validated_data):
        diagnoses = validated_data.pop("diagnoses", None)
        vitals = validated_data.pop("vital_signs", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if diagnoses is not None:
            instance.diagnoses.all().delete()
            for d in diagnoses:
                Diagnosis.objects.create(consultation=instance, patient=instance.patient, **d)
        if vitals is not None:
            for v in vitals:
                VitalSigns.objects.create(consultation=instance, patient=instance.patient,
                                          recorded_by=self.context["request"].user, **v)
        return instance


class ReferralSerializer(serializers.ModelSerializer):
    patient_details = PatientSummarySerializer(source="patient", read_only=True)
    from_doctor_name = serializers.CharField(source="from_doctor.get_full_name", read_only=True)
    to_doctor_name = serializers.CharField(source="to_doctor.get_full_name", read_only=True)
    department_name = serializers.CharField(source="to_department.name", read_only=True)
    diagnosis_name = serializers.CharField(source="diagnosis.name", read_only=True)

    class Meta:
        model = Referral
        fields = "__all__"
        read_only_fields = ["from_doctor", "created_by", "updated_by", "completed_at"]

    def validate(self, attrs):
        request = self.context["request"]
        doctor = attrs.get("to_doctor", getattr(self.instance, "to_doctor", None))
        if doctor and not doctor.in_roles("doctor"):
            raise serializers.ValidationError({"to_doctor": "The receiving user must be a doctor."})
        consultation = attrs.get("consultation", getattr(self.instance, "consultation", None))
        diagnosis = attrs.get("diagnosis", getattr(self.instance, "diagnosis", None))
        if diagnosis and consultation and diagnosis.consultation_id != consultation.id:
            raise serializers.ValidationError({"diagnosis": "Diagnosis must belong to the selected consultation."})
        return attrs
