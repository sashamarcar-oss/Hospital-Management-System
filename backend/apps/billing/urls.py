from rest_framework.routers import DefaultRouter

from apps.billing.views import ChargeTypeViewSet, InvoiceViewSet, PaymentViewSet

router = DefaultRouter()
router.register("charge-types", ChargeTypeViewSet, basename="charge-type")
router.register("payments", PaymentViewSet, basename="payment")
router.register("", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
