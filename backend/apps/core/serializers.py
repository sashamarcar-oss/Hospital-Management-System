from django.conf import settings
from rest_framework import serializers

from apps.core.models import AuditLog, Document, Notification


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "user", "user_name", "action", "module", "record", "object_id",
                  "ip_address", "user_agent", "previous_value", "new_value", "description", "created_at"]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return "System"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "message", "link", "is_read", "created_at"]
        read_only_fields = ["id", "type", "title", "message", "link", "created_at"]


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "patient", "patient_name", "title", "category", "description",
                  "file", "file_url", "content_type", "size_bytes", "uploaded_by",
                  "uploaded_by_name", "created_at"]
        read_only_fields = ["content_type", "size_bytes", "uploaded_by", "created_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def validate_file(self, file):
        if file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size must not exceed {settings.MAX_UPLOAD_SIZE_MB} MB."
            )
        content_type = getattr(file, "content_type", "")
        if content_type and content_type not in settings.ALLOWED_DOCUMENT_TYPES:
            raise serializers.ValidationError(
                "This file type is not allowed. Upload a PDF, image, or document file."
            )
        return file
