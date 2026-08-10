from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasPermission
from apps.core.models import AuditLog
from apps.core.services import audit_log
from apps.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    StockMovement,
    Supplier,
)
from apps.inventory.serializers import (
    InventoryItemSerializer,
    PurchaseOrderSerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
    SupplierSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [HasPermission]
    code = "inventory.view"
    write_code = "inventory.update"
    search_fields = ["name", "contact_person", "phone", "email"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name"]


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related("supplier").all()
    serializer_class = InventoryItemSerializer
    permission_classes = [HasPermission]
    code = "inventory.view"
    write_code = "inventory.update"
    search_fields = ["name", "sku", "category"]
    filterset_fields = ["category", "supplier", "is_active"]
    ordering_fields = ["name", "quantity"]

    def perform_create(self, serializer):
        item = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inventory.item",
                  record=item.name, object_id=item.id, request=self.request)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def adjust_stock(self, request, pk=None):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.get_object()
        quantity = serializer.validated_data["quantity"]
        if item.quantity + quantity < 0:
            return Response({"detail": "Insufficient stock."}, status=400)
        item.quantity += quantity
        item.save(update_fields=["quantity"])
        StockMovement.objects.create(
            item=item,
            movement_type=StockMovement.MOVEMENT_ADJUSTMENT,
            quantity=quantity,
            balance_after=item.quantity,
            notes=serializer.validated_data.get("reason", ""),
            performed_by=request.user,
        )
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inventory.item",
                  record=item.name, object_id=item.id, request=request,
                  description=f"stock adjusted by {quantity:+d}")
        return Response(InventoryItemSerializer(item).data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        qs = [item for item in self.get_queryset() if item.is_low_stock]
        return Response(InventoryItemSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def movements(self, request):
        qs = StockMovement.objects.select_related("item", "performed_by").all()[:200]
        return Response(StockMovementSerializer(qs, many=True).data)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier").all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [HasPermission]
    code = "inventory.view"
    write_code = "inventory.update"
    filterset_fields = ["status", "supplier"]
    search_fields = ["po_number", "supplier__name"]
    ordering_fields = ["order_date"]

    def perform_create(self, serializer):
        po = serializer.save(created_by=self.request.user)
        audit_log(self.request.user, AuditLog.ACTION_CREATE, "inventory.purchaseorder",
                  record=po.po_number, object_id=po.id, request=self.request)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Receive stock against purchase order items."""
        po = self.get_object()
        if po.status == PurchaseOrder.STATUS_CANCELLED:
            return Response({"detail": "Cannot receive against a cancelled purchase order."}, status=400)
        for line in request.data.get("lines", []):
            po_item = PurchaseOrderItem.objects.select_for_update().get(pk=line["purchase_order_item"])
            qty = int(line["quantity"])
            remaining = po_item.quantity - po_item.received_quantity
            if qty <= 0 or qty > remaining:
                return Response({"detail": f"Invalid receive quantity for {po_item.item.name}."}, status=400)
            po_item.received_quantity += qty
            po_item.save(update_fields=["received_quantity"])
            po_item.item.quantity += qty
            po_item.item.save(update_fields=["quantity"])
            StockMovement.objects.create(
                item=po_item.item,
                movement_type=StockMovement.MOVEMENT_RECEIVE,
                quantity=qty,
                balance_after=po_item.item.quantity,
                reference=po.po_number,
                notes=f"Received against {po.po_number}",
                performed_by=request.user,
            )
        all_received = all(i.received_quantity >= i.quantity for i in po.items.all())
        some_received = any(i.received_quantity > 0 for i in po.items.all())
        if all_received:
            po.status = PurchaseOrder.STATUS_RECEIVED
        elif some_received:
            po.status = PurchaseOrder.STATUS_PARTIALLY_RECEIVED
        po.save()
        audit_log(request.user, AuditLog.ACTION_UPDATE, "inventory.purchaseorder",
                  record=po.po_number, object_id=po.id, request=request, description="stock received")
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def mark_ordered(self, request, pk=None):
        po = self.get_object()
        po.status = PurchaseOrder.STATUS_ORDERED
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        po.status = PurchaseOrder.STATUS_CANCELLED
        po.save()
        return Response(PurchaseOrderSerializer(po).data)
