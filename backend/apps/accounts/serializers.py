from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Permission, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "module"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.SerializerMethodField()
    dashboard_path = serializers.CharField(read_only=True)

    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "permissions", "permission_codes", "dashboard_path"]

    def get_permission_codes(self, obj):
        return list(obj.permissions.values_list("code", flat=True))


class UserBriefSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "role_code", "role_name", "profile_photo", "is_active", "is_patient_account",
        ]


class UserSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    permission_codes = serializers.SerializerMethodField()
    dashboard_path = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "phone",
            "role", "role_code", "role_name", "permission_codes", "dashboard_path",
            "department", "profile_photo", "is_active", "is_patient_account", "password",
            "date_joined",
        ]
        read_only_fields = ["date_joined"]

    def get_permission_codes(self, obj):
        if obj.role:
            if obj.role.code == Role.CODE_SUPER_ADMIN:
                from apps.accounts.permission_catalog import flat_permission_codes

                return flat_permission_codes()
            return list(obj.role.permissions.values_list("code", flat=True))
        return []

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role_code
        token["full_name"] = user.get_full_name()
        return token


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer(read_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class RoleUpdateSerializer(serializers.Serializer):
    """Used by admins to change a user's role / permissions."""

    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
    is_active = serializers.BooleanField(required=False)


class RegisterPatientSerializer(serializers.ModelSerializer):
    """Self-registration for the Patient role."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = Role.objects.filter(code=Role.CODE_PATIENT).first()
        user = User.objects.create(**validated_data, role=role, is_patient_account=True)
        user.set_password(password)
        user.save()
        return user
