import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission, IsPatientAccountOwner
from apps.core.models import AuditLog, Document, Notification
from apps.core.serializers import AuditLogSerializer, DocumentSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit logs — readable only by authorized administrators."""

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [HasPermission]
    code = "audit.view"
    filterset_fields = ["action", "module", "user"]
    search_fields = ["record", "description", "user__username"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [HasPermission]
    code = "notifications.view"

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=True, methods=["post"])
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = False
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.select_related("patient", "uploaded_by").all()
    serializer_class = DocumentSerializer
    permission_classes = [HasPermission, IsPatientAccountOwner]
    code = "documents.view"
    write_code = "documents.upload"
    filterset_fields = ["patient", "category"]
    search_fields = ["title", "description", "patient__first_name", "patient__last_name"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        uploaded_file = serializer.validated_data.get("file")
        document = serializer.save(uploaded_by=self.request.user)
        if uploaded_file:
            document.content_type = getattr(uploaded_file, "content_type", "")
            document.size_bytes = getattr(uploaded_file, "size", 0)
        document.save(update_fields=["content_type", "size_bytes"])
        from apps.core.services import audit_log

        audit_log(self.request.user, AuditLog.ACTION_UPLOAD, "core.document",
                  record=document.title, object_id=document.id, request=self.request)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        from apps.core.services import audit_log

        audit_log(request.user, AuditLog.ACTION_DOWNLOAD, "core.document",
                  record=document.title, object_id=document.id, request=request)
        response = Response(status=302)
        response["Location"] = document.file.url
        return response
