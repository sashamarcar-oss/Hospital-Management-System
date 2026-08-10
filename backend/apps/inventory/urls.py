from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    InventoryItemViewSet,
    PurchaseOrderViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("", InventoryItemViewSet, basename="inventory-item")

urlpatterns = router.urls
