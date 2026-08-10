from rest_framework.routers import DefaultRouter

from apps.emergency.views import EmergencyVisitViewSet

router = DefaultRouter()
router.register("", EmergencyVisitViewSet, basename="emergency-visit")

urlpatterns = router.urls
