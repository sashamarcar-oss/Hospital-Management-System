from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inpatient.views import (
    NursingDashboardView,
    NursingHandoverViewSet,
    NursingNoteViewSet,
)

router = DefaultRouter()
router.register("notes", NursingNoteViewSet, basename="nursing-note")
router.register("handovers", NursingHandoverViewSet, basename="nursing-handover")

urlpatterns = [
    path("dashboard/", NursingDashboardView.as_view(), name="nursing-dashboard"),
] + router.urls
