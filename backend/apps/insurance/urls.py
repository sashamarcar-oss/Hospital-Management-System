from rest_framework.routers import DefaultRouter

from apps.insurance.views import (
    InsuranceClaimViewSet,
    InsurancePolicyViewSet,
    InsuranceProviderViewSet,
)

router = DefaultRouter()
router.register("providers", InsuranceProviderViewSet, basename="insurance-provider")
router.register("policies", InsurancePolicyViewSet, basename="insurance-policy")
router.register("claims", InsuranceClaimViewSet, basename="insurance-claim")

urlpatterns = router.urls
