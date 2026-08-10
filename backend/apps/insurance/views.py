from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.insurance.models import InsuranceClaim, InsurancePolicy, InsuranceProvider
from apps.insurance.serializers import (
    InsuranceClaimSerializer,
    InsurancePolicySerializer,
    InsuranceProviderSerializer,
)


class InsuranceProviderViewSet(viewsets.ModelViewSet):
    queryset = InsuranceProvider.objects.all()
    serializer_class = InsuranceProviderSerializer
    permission_classes = [HasPermission]
    code = "insurance.view"
    write_code = "insurance.create"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name"]


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.select_related("patient", "provider").all()
    serializer_class = InsurancePolicySerializer
    permission_classes = [HasPermission]
    code = "insurance.view"
    write_code = "insurance.create"
    filterset_fields = ["status", "patient", "provider", "coverage_type"]
    search_fields = ["policy_number", "membership_number", "patient__first_name", "patient__last_name"]
    ordering_fields = ["start_date"]

    def perform_create(self, serializer):
        policy = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "insurance.policy",
                  record=policy.policy_number, object_id=policy.id, request=self.request)


class InsuranceClaimViewSet(viewsets.ModelViewSet):
    queryset = InsuranceClaim.objects.select_related("policy__provider", "patient", "invoice").all()
    serializer_class = InsuranceClaimSerializer
    permission_classes = [HasPermission]
    code = "insurance.manage_claims"
    filterset_fields = ["status", "patient", "policy", "invoice"]
    search_fields = ["claim_number", "patient__first_name", "patient__last_name"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.in_roles("patient"):
            linked = getattr(user, "patient_account", None)
            return qs.filter(patient=linked) if linked else qs.none()
        return qs

    def perform_create(self, serializer):
        claim = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "insurance.claim",
                  record=claim.claim_number, object_id=claim.id, request=self.request)

    def _transition(self, request, claim, new_status, description, extra=None):
        previous = {"status": claim.status}
        for attr, value in (extra or {}).items():
            setattr(claim, attr, value)
        if new_status == InsuranceClaim.STATUS_SUBMITTED and not claim.submitted_date:
            claim.submitted_date = timezone.now().date()
        if new_status in (InsuranceClaim.STATUS_APPROVED, InsuranceClaim.STATUS_PARTIALLY_APPROVED,
                          InsuranceClaim.STATUS_REJECTED):
            claim.approval_date = timezone.now().date()
        claim.status = new_status
        claim.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "insurance.claim",
                  record=claim.claim_number, object_id=claim.id, request=request,
                  previous_value=previous, new_value={"status": claim.status},
                  description=description)
        return Response(InsuranceClaimSerializer(claim).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        claim = self.get_object()
        return self._transition(request, claim, InsuranceClaim.STATUS_SUBMITTED, "submitted")

    @action(detail=True, methods=["post"])
    def start_review(self, request, pk=None):
        claim = self.get_object()
        return self._transition(request, claim, InsuranceClaim.STATUS_UNDER_REVIEW, "under review")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        claim = self.get_object()
        amount = request.data.get("approved_amount")
        return self._transition(request, claim, InsuranceClaim.STATUS_APPROVED, "approved",
                                extra={"approved_amount": amount})

    @action(detail=True, methods=["post"])
    def partial_approve(self, request, pk=None):
        claim = self.get_object()
        approved = request.data.get("approved_amount")
        rejected = request.data.get("rejected_amount")
        contribution = request.data.get("patient_contribution")
        return self._transition(
            request, claim, InsuranceClaim.STATUS_PARTIALLY_APPROVED, "partially approved",
            extra={"approved_amount": approved, "rejected_amount": rejected,
                   "patient_contribution": contribution},
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        claim = self.get_object()
        return self._transition(request, claim, InsuranceClaim.STATUS_REJECTED, "rejected")

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        claim = self.get_object()
        return self._transition(request, claim, InsuranceClaim.STATUS_PAID, "paid",
                                extra={"approved_amount": request.data.get("approved_amount") or claim.approved_amount})
