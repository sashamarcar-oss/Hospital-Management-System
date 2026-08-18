from rest_framework.routers import DefaultRouter

from apps.inpatient.views import InpatientVitalsViewSet

router = DefaultRouter()
router.register("", InpatientVitalsViewSet, basename="vitals")

urlpatterns = router.urls
