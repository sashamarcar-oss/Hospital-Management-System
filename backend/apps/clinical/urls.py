from rest_framework.routers import DefaultRouter

from apps.clinical.views import (
    ConsultationViewSet,
    DiagnosisViewSet,
    PrescriptionViewSet,
    ReferralViewSet,
    VitalSignsViewSet,
)

router = DefaultRouter()
router.register("vitals", VitalSignsViewSet, basename="vitals")
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")
router.register("referrals", ReferralViewSet, basename="referral")
router.register("", ConsultationViewSet, basename="consultation")

urlpatterns = router.urls
