from rest_framework.routers import DefaultRouter

from apps.inpatient.views import (
    AdmissionViewSet,
    BedViewSet,
    DischargeViewSet,
    ICUMonitoringRecordViewSet,
    NursingHandoverViewSet,
    NursingNoteViewSet,
    RoomViewSet,
    WardViewSet,
)

router = DefaultRouter()
router.register("wards", WardViewSet, basename="ward")
router.register("rooms", RoomViewSet, basename="room")
router.register("beds", BedViewSet, basename="bed")
router.register("discharges", DischargeViewSet, basename="discharge")
router.register("nursing-notes", NursingNoteViewSet, basename="nursing-note")
router.register("nursing-handovers", NursingHandoverViewSet, basename="nursing-handover")
router.register("icu-monitoring", ICUMonitoringRecordViewSet, basename="icu-monitoring")
router.register("", AdmissionViewSet, basename="admission")

urlpatterns = router.urls
