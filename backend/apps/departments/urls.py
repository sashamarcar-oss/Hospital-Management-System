from rest_framework.routers import DefaultRouter

from apps.departments.views import DepartmentViewSet

router = DefaultRouter()
router.register("", DepartmentViewSet, basename="department")

urlpatterns = router.urls
