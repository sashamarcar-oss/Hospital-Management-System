from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.pharmacy.views import DispenseView, MedicineCategoryViewSet, MedicineViewSet

router = DefaultRouter()
router.register("categories", MedicineCategoryViewSet, basename="medicine-category")
router.register("medicines", MedicineViewSet, basename="medicine")

urlpatterns = [
    path("dispense/", DispenseView.as_view({"post": "create"}), name="dispense"),
] + router.urls
