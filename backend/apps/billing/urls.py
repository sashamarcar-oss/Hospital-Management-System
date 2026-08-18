from rest_framework.routers import DefaultRouter

from apps.billing.views import (
    ChargeTypeViewSet,
    InvoiceViewSet,
    PaymentGatewayTransactionViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register("charge-types", ChargeTypeViewSet, basename="charge-type")
router.register("payments", PaymentViewSet, basename="payment")
router.register("gateway-transactions", PaymentGatewayTransactionViewSet, basename="gateway-transaction")
router.register("", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
