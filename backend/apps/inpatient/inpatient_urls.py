from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.inpatient.views import (
    AdmissionViewSet,
    BedAssignmentViewSet,
    BedViewSet,
    DischargeViewSet,
    InpatientStatsView,
    NurseAssignmentViewSet,
    RoomViewSet,
    TimelineExportView,
    TransferViewSet,
    WardViewSet,
)

router = DefaultRouter()
router.register("wards", WardViewSet, basename="ward")
router.register("rooms", RoomViewSet, basename="room")
router.register("beds", BedViewSet, basename="bed")
router.register("bed-assignments", BedAssignmentViewSet, basename="bed-assignment")
router.register("transfers", TransferViewSet, basename="transfer")
router.register("nurse-assignments", NurseAssignmentViewSet, basename="nurse-assignment")
router.register("discharges", DischargeViewSet, basename="discharge")
router.register("admissions", AdmissionViewSet, basename="admission")

urlpatterns = [
    path("stats/", InpatientStatsView.as_view(), name="inpatient-stats"),
    path("timeline/", TimelineExportView.as_view(), name="timeline-export"),
] + router.urls
