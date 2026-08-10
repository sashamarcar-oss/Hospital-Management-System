from rest_framework.routers import DefaultRouter

from apps.laboratory.views import (
    LabRequestViewSet,
    LabResultViewSet,
    LabTestCatalogViewSet,
)

router = DefaultRouter()
router.register("catalog", LabTestCatalogViewSet, basename="lab-test")
router.register("results", LabResultViewSet, basename="lab-result")
router.register("", LabRequestViewSet, basename="lab-request")

urlpatterns = router.urls
