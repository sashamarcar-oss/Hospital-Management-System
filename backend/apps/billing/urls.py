from rest_framework.routers import DefaultRouter

from apps.billing.views import (
    ChargeTypeViewSet,
    InvoiceItemViewSet,
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

# Add custom nested routes for invoice items manually
from django.urls import path

# Reusable nested routes for invoice items
invoice_items_list = InvoiceItemViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
invoice_items_detail = InvoiceItemViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns += [
    path('<int:invoice_pk>/items/', invoice_items_list, name='invoice-items-list'),
    path('<int:invoice_pk>/items/<int:pk>/', invoice_items_detail, name='invoice-items-detail'),
]
