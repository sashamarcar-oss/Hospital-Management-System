from rest_framework.routers import DefaultRouter

from apps.core.views import AuditLogViewSet, DocumentViewSet, NotificationViewSet

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
