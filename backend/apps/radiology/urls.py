from rest_framework.routers import DefaultRouter

from apps.radiology.views import RadiologyReportViewSet, RadiologyRequestViewSet

router = DefaultRouter()
router.register("reports", RadiologyReportViewSet, basename="radiology-report")
router.register("", RadiologyRequestViewSet, basename="radiology-request")

urlpatterns = router.urls
