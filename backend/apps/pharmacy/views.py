from django.db import transaction, models
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import HasPermission
from apps.clinical.models import Prescription, PrescriptionItem
from apps.core.models import AuditLog
from apps.core.services import audit_log, notify
from apps.pharmacy.models import (
    Medicine,
    MedicineBatch,
    MedicineCategory,
    MedicineStockMovement,
)
from apps.pharmacy.serializers import (
    MedicineBatchSerializer,
    MedicineCategorySerializer,
    MedicineSerializer,
    MedicineStockInSerializer,
    MedicineStockMovementSerializer,
    StockAdjustmentSerializer,
)


class MedicineCategoryViewSet(viewsets.ModelViewSet):
    queryset = MedicineCategory.objects.all()
    serializer_class = MedicineCategorySerializer
    permission_classes = [HasPermission]
    code = "pharmacy.view"
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name"]


class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.prefetch_related("batches").all()
    serializer_class = MedicineSerializer
    permission_classes = [HasPermission]
    code = "pharmacy.view"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "generic_name", "brand_name", "manufacturer"]
    filterset_fields = ["category", "is_active", "requires_prescription"]
    ordering_fields = ["name", "created_at"]

    @transaction.atomic
    def perform_create(self, serializer):
        batch_number = serializer.validated_data.pop("initial_batch_number", None)
        quantity = serializer.validated_data.pop("initial_quantity", None)
        expiry_date = serializer.validated_data.pop("initial_expiry_date", None)
        supplier = serializer.validated_data.pop("initial_supplier", "")
        batch_price = serializer.validated_data.pop("initial_purchase_price", None)
        medicine = serializer.save()
        if batch_number and quantity:
            batch = MedicineBatch.objects.create(
                medicine=medicine,
                batch_number=batch_number,
                quantity=quantity,
                purchase_price=batch_price or medicine.purchase_price,
                expiry_date=expiry_date,
                supplier=supplier,
            )
            MedicineStockMovement.objects.create(
                medicine=medicine,
                batch=batch,
                movement_type=MedicineStockMovement.MOVEMENT_RECEIVE,
                quantity=quantity,
                balance_after=medicine.total_stock,
                reference="initial_stock",
                notes=f"Initial batch {batch_number}",
                performed_by=self.request.user,
            )

    @property
    def _stock_qs(self):
        return self.queryset.all()

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def stock_in(self, request, pk=None):
        """Receive a new batch of stock for the medicine."""
        serializer = MedicineStockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        medicine = self.get_object()
        data = serializer.validated_data
        batch = MedicineBatch.objects.create(medicine=medicine, **data)
        MedicineStockMovement.objects.create(
            medicine=medicine,
            batch=batch,
            movement_type=MedicineStockMovement.MOVEMENT_RECEIVE,
            quantity=data["quantity"],
            balance_after=medicine.total_stock,
            reference="stock_in",
            notes=f"Received batch {data['batch_number']}",
            performed_by=request.user,
        )
        audit_log(request.user, AuditLog.ACTION_CREATE, "pharmacy.medicine",
                  record=medicine.name, object_id=medicine.id, request=request,
                  description=f"stock received batch {data['batch_number']} qty {data['quantity']}")
        return Response(MedicineSerializer(medicine).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def adjust_stock(self, request, pk=None):
        """Manual stock adjustment (+/-) with a recorded reason."""
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        medicine = self.get_object()
        data = serializer.validated_data
        quantity = data["quantity"]
        batch = data.get("batch_id")
        if quantity < 0 and batch and batch.quantity + quantity < 0:
            return Response({"detail": "Insufficient stock in the selected batch."}, status=400)
        if batch:
            batch.quantity += quantity
            batch.save(update_fields=["quantity"])
        MedicineStockMovement.objects.create(
            medicine=medicine,
            batch=batch,
            movement_type=MedicineStockMovement.MOVEMENT_ADJUSTMENT,
            quantity=quantity,
            balance_after=medicine.total_stock,
            reference="manual_adjustment",
            notes=data.get("reason", ""),
            performed_by=request.user,
        )
        audit_log(request.user, AuditLog.ACTION_UPDATE, "pharmacy.medicine",
                  record=medicine.name, object_id=medicine.id, request=request,
                  description=f"stock adjusted by {quantity:+d}")
        return Response(MedicineSerializer(medicine).data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        qs = [m for m in self._stock_qs if m.is_low_stock]
        return Response(MedicineSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        from datetime import timedelta
        days = int(request.query_params.get("days", 90))
        today = timezone.now().date()
        qs = MedicineBatch.objects.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=days)).select_related("medicine")
        return Response(MedicineBatchSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def expired(self, request):
        qs = MedicineBatch.objects.filter(expiry_date__lt=timezone.now().date()).select_related("medicine")
        return Response(MedicineBatchSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def stock_movements(self, request):
        qs = MedicineStockMovement.objects.select_related("medicine", "batch", "performed_by").all()
        return Response(MedicineStockMovementSerializer(qs[:200], many=True).data)


class DispenseView(viewsets.ViewSet):
    """Pharmacist dispensing. Deducts stock and updates the prescription."""

    permission_classes = [HasPermission]
    code = "pharmacy.dispense"

    @transaction.atomic
    def create(self, request):
        prescription_id = request.data.get("prescription")
        items = request.data.get("items", [])
        try:
            prescription = Prescription.objects.select_for_update().get(pk=prescription_id)
        except Prescription.DoesNotExist:
            return Response({"detail": "Prescription not found."}, status=404)

        if prescription.status in (Prescription.STATUS_DISPENSED, Prescription.STATUS_CANCELLED):
            return Response({"detail": "This prescription cannot be dispensed."}, status=400)

        for item_data in items:
            item_id = item_data.get("item")
            qty = int(item_data.get("quantity", 0))
            try:
                item = prescription.items.get(pk=item_id)
            except PrescriptionItem.DoesNotExist:
                return Response({"detail": f"Prescription item {item_id} not found."}, status=400)
            if qty <= 0 or qty > (item.quantity - item.dispensed_quantity):
                return Response({"detail": f"Invalid quantity for {item.medicine.name}."}, status=400)
            self._deduct_medicine(item.medicine, qty, request.user, f"prescription {prescription.id}")
            item.dispensed_quantity += qty
            item.save(update_fields=["dispensed_quantity"])

        prescription.dispensed_by = request.user
        prescription.dispensed_at = timezone.now()
        prescription.update_status()

        self._create_billing_charge(prescription)

        audit_log(request.user, AuditLog.ACTION_DISPENSE, "pharmacy.dispense",
                  record=str(prescription.patient), object_id=prescription.id,
                  request=request, description=f"dispensed prescription {prescription.id}")
        if prescription.patient.user:
            notify(prescription.patient.user, "Medication dispensed",
                   "Your prescription has been dispensed at the pharmacy.",
                   notification_type="prescription", link="/portal")

        from apps.clinical.serializers import PrescriptionSerializer

        return Response(PrescriptionSerializer(prescription).data)

    def _deduct_medicine(self, medicine, quantity, user, reference):
        today = timezone.now().date()
        remaining = quantity
        batches = medicine.batches.exclude(quantity=0).filter(models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=today)).order_by("expiry_date", "id")
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.quantity, remaining)
            batch.quantity -= take
            batch.save(update_fields=["quantity"])
            remaining -= take
            MedicineStockMovement.objects.create(
                medicine=medicine,
                batch=batch,
                movement_type=MedicineStockMovement.MOVEMENT_DISPENSE,
                quantity=-take,
                balance_after=medicine.total_stock,
                reference=reference,
                performed_by=user,
            )
        if remaining > 0:
            from rest_framework import exceptions
            audit_log(user, AuditLog.ACTION_OTHER, "pharmacy.expiry", record=medicine.name, description="dispensing blocked: no valid non-expired stock")
            raise exceptions.ValidationError(f"Insufficient stock for {medicine.name}.")

    def _create_billing_charge(self, prescription):
        """Generate medication charges on the patient's open invoice."""
        try:
            from apps.billing.models import Invoice, InvoiceItem
            from apps.billing.utils import get_or_create_open_invoice

            invoice = get_or_create_open_invoice(prescription.patient, created_by=prescription.dispensed_by)
            for item in prescription.items.all():
                if item.dispensed_quantity and not hasattr(item, "billing_item"):
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=f"{item.medicine.name} ({item.dosage})",
                        quantity=item.dispensed_quantity,
                        unit_price=item.medicine.selling_price,
                        medicine_item=item,
                    )
        except Exception:
            pass
