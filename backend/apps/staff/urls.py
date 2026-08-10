from rest_framework.routers import DefaultRouter

from apps.staff.views import AttendanceViewSet, LeaveRequestViewSet, ShiftViewSet, StaffViewSet

router = DefaultRouter()
# Specific prefixes must be registered before the "" (staff) prefix so that
# Django's URL resolver matches them ahead of the generic <pk> pattern.
router.register("shifts", ShiftViewSet, basename="shift")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("leaves", LeaveRequestViewSet, basename="leave")
router.register("", StaffViewSet, basename="staff")

urlpatterns = router.urls
