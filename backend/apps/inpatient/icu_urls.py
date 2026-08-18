from rest_framework.routers import DefaultRouter

from apps.inpatient.views import (
    FluidBalanceViewSet,
    ICUMonitoringRecordViewSet,
    ICUMonitoringSheetViewSet,
    ICUThresholdViewSet,
)

router = DefaultRouter()
router.register("sheets", ICUMonitoringSheetViewSet, basename="icu-sheet")
router.register("thresholds", ICUThresholdViewSet, basename="icu-threshold")
router.register("monitoring", ICUMonitoringRecordViewSet, basename="icu-monitoring")
router.register("fluid-balance", FluidBalanceViewSet, basename="fluid-balance")

urlpatterns = router.urls
