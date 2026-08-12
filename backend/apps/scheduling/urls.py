from rest_framework.routers import DefaultRouter
from apps.scheduling.views import NurseShiftViewSet
router = DefaultRouter(); router.register("", NurseShiftViewSet, basename="nurse-shift")
urlpatterns = router.urls
