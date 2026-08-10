from rest_framework import serializers

from apps.patients.models import EmergencyContact, Patient


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "name", "phone", "relationship", "address"]


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, required=False)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_number", "user", "first_name", "middle_name", "last_name",
            "full_name", "date_of_birth", "age", "gender", "national_id", "phone",
            "email", "address", "occupation", "marital_status", "blood_group",
            "allergies", "insurance_provider", "insurance_number", "next_of_kin_name",
            "next_of_kin_phone", "next_of_kin_relationship", "profile_photo",
            "is_active", "emergency_contacts", "created_at",
        ]
        read_only_fields = ["patient_number", "created_at"]

    def create(self, validated_data):
        contacts = validated_data.pop("emergency_contacts", [])
        patient = Patient.objects.create(**validated_data)
        for contact in contacts:
            EmergencyContact.objects.create(patient=patient, **contact)
        return patient

    def update(self, instance, validated_data):
        contacts = validated_data.pop("emergency_contacts", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if contacts is not None:
            instance.emergency_contacts.all().delete()
            for contact in contacts:
                EmergencyContact.objects.create(patient=instance, **contact)
        return instance


class PatientSummarySerializer(serializers.ModelSerializer):
    """Lightweight representation used across modules."""

    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = ["id", "patient_number", "first_name", "middle_name", "last_name",
                  "full_name", "date_of_birth", "age", "gender", "phone", "email",
                  "blood_group", "allergies", "insurance_provider", "insurance_number"]
