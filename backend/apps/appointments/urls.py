from rest_framework.routers import DefaultRouter

from apps.appointments.views import AppointmentViewSet, QueueViewSet

router = DefaultRouter()
router.register("queue", QueueViewSet, basename="queue")
router.register("", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls
