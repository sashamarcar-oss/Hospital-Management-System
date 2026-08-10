import { useState } from "react";
import { CheckCircle2, Loader2, PackagePlus, Plus, ShoppingCart, Trash2, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { InventoryItem, Paginated, PurchaseOrder, Supplier } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { PO_STATUS_LABELS } from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/utils";

export function PurchaseOrdersPage() {
  const { data: orders, isLoading } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: () =>
      api
        .get<Paginated<PurchaseOrder>>("/inventory/purchase-orders/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });

  return (
    <div className="space-y-6">
      <PageHeader title="Purchase orders" description="Order and receive stock from suppliers.">
        <NewPurchaseOrderDialog onDone={invalidate} />
      </PageHeader>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (orders?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No purchase orders.</p>
      ) : (
        <div className="space-y-4">
          {(orders?.results ?? []).map((po) => (
            <Card key={po.id}>
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {po.po_number} · {po.supplier_name}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      Ordered {formatDate(po.order_date)}
                      {po.expected_date ? ` · expected ${formatDate(po.expected_date)}` : ""} ·{" "}
                      {formatCurrency(po.total_cost)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={po.status} labels={PO_STATUS_LABELS} />
                    <POActions po={po} onDone={invalidate} />
                  </div>
                </div>
                <div className="mt-3 divide-y rounded-lg border">
                  {po.items.map((item) => (
                    <div key={item.id} className="flex items-center justify-between p-2.5 text-sm">
                      <div>
                        <p className="font-medium">{item.item_name}</p>
                        <p className="text-muted-foreground text-xs">
                          received {item.received_quantity} / {item.quantity}
                        </p>
                      </div>
                      <p className="text-muted-foreground">
                        {item.quantity} × {formatCurrency(item.unit_price)}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function POActions({ po, onDone }: { po: PurchaseOrder; onDone: () => void }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (action: string) => api.post(`/inventory/purchase-orders/${po.id}/${action}/`),
    onSuccess: () => {
      success("Purchase order updated");
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Action failed.")),
  });

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {po.status === "draft" && (
        <Button variant="outline" size="sm" onClick={() => mutation.mutate("mark_ordered")}>
          <ShoppingCart /> Mark ordered
        </Button>
      )}
      {(po.status === "draft" || po.status === "ordered" || po.status === "partially_received") && (
        <ReceiveDialog po={po} onDone={onDone} />
      )}
      {(po.status === "draft" || po.status === "ordered") && (
        <Button variant="ghost" size="sm" onClick={() => mutation.mutate("cancel")}>
          <XCircle /> Cancel
        </Button>
      )}
    </div>
  );
}

function ReceiveDialog({ po, onDone }: { po: PurchaseOrder; onDone: () => void }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [quantities, setQuantities] = useState<Record<number, string>>({});

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/inventory/purchase-orders/${po.id}/receive/`, {
        lines: po.items
          .filter((i) => Number(quantities[i.id] ?? 0) > 0)
          .map((i) => ({ purchase_order_item: i.id, quantity: Number(quantities[i.id]) })),
      }),
    onSuccess: () => {
      success("Stock received", "Quantities added to inventory.");
      setQuantities({});
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to receive stock.")),
  });

  const any = po.items.some((i) => Number(quantities[i.id] ?? 0) > 0);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <PackagePlus /> Receive
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Receive stock — {po.po_number}</DialogTitle>
          <DialogDescription>Enter the quantity received for each line item.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {po.items.map((item) => {
            const remaining = item.quantity - item.received_quantity;
            return (
              <div key={item.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{item.item_name}</p>
                  <p className="text-muted-foreground text-xs">
                    {item.quantity} ordered · {item.received_quantity} received · {remaining} remaining
                  </p>
                </div>
                <div className="w-28">
                  <Input
                    type="number"
                    min={0}
                    max={remaining}
                    value={quantities[item.id] ?? ""}
                    placeholder={`≤ ${remaining}`}
                    onChange={(e) => setQuantities((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!any || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <CheckCircle2 /> Receive
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NewPurchaseOrderDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [supplier, setSupplier] = useState("");
  const [expectedDate, setExpectedDate] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<{ item: string; quantity: string; unit_price: string }[]>([]);

  const { data: suppliers } = useQuery({
    queryKey: ["inventory", "suppliers", "options"],
    queryFn: () =>
      api.get<Paginated<Supplier>>("/inventory/suppliers/", { params: { page_size: 200 } }).then((r) => r.data),
  });
  const { data: items } = useQuery({
    queryKey: ["inventory", "items", "options"],
    queryFn: () =>
      api.get<Paginated<InventoryItem>>("/inventory/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/inventory/purchase-orders/", {
        supplier: Number(supplier),
        expected_date: expectedDate || null,
        notes,
        items: lines
          .filter((l) => l.item && Number(l.quantity) > 0)
          .map((l) => ({
            item: Number(l.item),
            quantity: Number(l.quantity),
            unit_price: Number(l.unit_price),
          })),
      }),
    onSuccess: () => {
      success("Purchase order created");
      setOpen(false);
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create purchase order.")),
  });

  const validLines = lines.filter((l) => l.item && Number(l.quantity) > 0).length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New purchase order
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Create purchase order</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Supplier</Label>
              <Select value={supplier} onValueChange={setSupplier}>
                <SelectTrigger><SelectValue placeholder="Select supplier" /></SelectTrigger>
                <SelectContent>
                  {(suppliers?.results ?? []).map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Expected date</Label>
              <Input type="date" value={expectedDate} onChange={(e) => setExpectedDate(e.target.value)} />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Line items</Label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setLines((prev) => [...prev, { item: "", quantity: "", unit_price: "" }])}
              >
                <Plus /> Add line
              </Button>
            </div>
            {lines.length === 0 ? (
              <p className="text-muted-foreground text-sm">No line items yet.</p>
            ) : (
              <div className="space-y-2">
                {lines.map((line, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Select
                      value={line.item}
                      onValueChange={(v) =>
                        setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, item: v } : l)))
                      }
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Item" />
                      </SelectTrigger>
                      <SelectContent>
                        {(items?.results ?? []).map((it) => (
                          <SelectItem key={it.id} value={String(it.id)}>
                            {it.name} ({it.sku})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      type="number"
                      min={1}
                      className="w-24"
                      placeholder="Qty"
                      value={line.quantity}
                      onChange={(e) =>
                        setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, quantity: e.target.value } : l)))
                      }
                    />
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      className="w-24"
                      placeholder="Price"
                      value={line.unit_price}
                      onChange={(e) =>
                        setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, unit_price: e.target.value } : l)))
                      }
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!(supplier && validLines) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <ShoppingCart /> Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
