import { useState } from "react";
import { AlertTriangle, Boxes, Loader2, Package, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { InventoryItem, Paginated, StockMovement } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { MOVEMENT_TYPE_LABELS } from "@/lib/constants";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export function InventoryPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Inventory" description="Stock levels, adjustments and movement history.">
        <NewItemDialog />
      </PageHeader>
      <Tabs defaultValue="items">
        <TabsList>
          <TabsTrigger value="items">Items</TabsTrigger>
          <TabsTrigger value="movements">Movements</TabsTrigger>
        </TabsList>
        <TabsContent value="items">
          <ItemsTab />
        </TabsContent>
        <TabsContent value="movements">
          <MovementsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ItemsTab() {
  const queryClient = useQueryClient();

  const { data: items, isLoading } = useQuery({
    queryKey: ["inventory", "items"],
    queryFn: () =>
      api.get<Paginated<InventoryItem>>("/inventory/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const { data: lowStock } = useQuery({
    queryKey: ["inventory", "low-stock"],
    queryFn: () => api.get<InventoryItem[]>("/inventory/low_stock/").then((r) => r.data),
  });

  const totalValue = (items?.results ?? []).reduce(
    (sum, i) => sum + Number(i.quantity) * Number(i.purchase_price),
    0
  );

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["inventory"] });
    queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={Boxes} title="Stock items" value={(items?.results ?? []).length} />
        <StatCard icon={Package} title="Stock value" value={formatCurrency(totalValue)} />
        <StatCard icon={AlertTriangle} title="Low stock" value={lowStock?.length ?? 0} />
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (items?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No inventory items.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="p-3 text-left font-medium">Item</th>
                <th className="p-3 text-left font-medium">SKU</th>
                <th className="p-3 text-left font-medium">Category</th>
                <th className="p-3 text-right font-medium">Qty</th>
                <th className="p-3 text-right font-medium">Reorder</th>
                <th className="p-3 text-right font-medium">Value</th>
                <th className="p-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {(items?.results ?? []).map((item) => (
                <tr key={item.id} className="hover:bg-muted/40">
                  <td className="p-3">
                    <p className="font-medium">{item.name}</p>
                    {item.is_low_stock && (
                      <span className="text-amber-600 text-xs">Low stock</span>
                    )}
                  </td>
                  <td className="p-3 text-muted-foreground">{item.sku}</td>
                  <td className="p-3">{item.category}</td>
                  <td className="p-3 text-right">
                    {item.quantity} {item.unit}
                  </td>
                  <td className="p-3 text-right text-muted-foreground">{item.reorder_level}</td>
                  <td className="p-3 text-right">{formatCurrency(Number(item.quantity) * Number(item.purchase_price))}</td>
                  <td className="p-3 text-right">
                    <AdjustStockDialog item={item} onDone={invalidate} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AdjustStockDialog({ item, onDone }: { item: InventoryItem; onDone: () => void }) {
  const { success, error } = useToast();
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/inventory/${item.id}/adjust_stock/`, {
        quantity: Number(quantity),
        reason,
      }),
    onSuccess: () => {
      success("Stock adjusted");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to adjust stock.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Adjust</Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Adjust stock — {item.name}</DialogTitle>
          <DialogDescription>
            Current quantity: {item.quantity} {item.unit}. Enter a positive or negative delta.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Quantity delta</Label>
            <Input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="e.g. 10 or -5"
            />
          </div>
          <div className="space-y-2">
            <Label>Reason</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!quantity || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NewItemDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [category, setCategory] = useState("");
  const [unit, setUnit] = useState("");
  const [reorderLevel, setReorderLevel] = useState("");
  const [purchasePrice, setPurchasePrice] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const [supplier, setSupplier] = useState<string>("");
  const [location, setLocation] = useState("");

  const { data: suppliers } = useQuery({
    queryKey: ["inventory", "suppliers", "options"],
    queryFn: () =>
      api.get<Paginated<{ id: number; name: string }>>("/inventory/suppliers/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/inventory/", {
        name,
        sku,
        category,
        unit,
        reorder_level: Number(reorderLevel) || 0,
        purchase_price: purchasePrice ? Number(purchasePrice) : null,
        selling_price: sellingPrice ? Number(sellingPrice) : null,
        supplier: supplier ? Number(supplier) : null,
        location,
      }),
    onSuccess: () => {
      success("Item added");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to add item.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New item
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add inventory item</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>SKU</Label>
              <Input value={sku} onChange={(e) => setSku(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Input value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Unit</Label>
              <Input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="pcs / box / l" />
            </div>
            <div className="space-y-2">
              <Label>Reorder level</Label>
              <Input type="number" min={0} value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Location</Label>
              <Input value={location} onChange={(e) => setLocation(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Purchase price</Label>
              <Input type="number" min={0} step="0.01" value={purchasePrice} onChange={(e) => setPurchasePrice(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Selling price</Label>
              <Input type="number" min={0} step="0.01" value={sellingPrice} onChange={(e) => setSellingPrice(e.target.value)} />
            </div>
          </div>
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
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Package /> Add
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MovementsTab() {
  const { data: movements, isLoading } = useQuery({
    queryKey: ["inventory", "movements"],
    queryFn: () => api.get<StockMovement[]>("/inventory/movements/").then((r) => r.data),
  });

  return (
    <div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (movements ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No stock movements yet.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(movements ?? []).map((m) => (
            <div key={m.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-medium">{m.item_name}</p>
                <p className="text-muted-foreground text-xs">
                  {MOVEMENT_TYPE_LABELS[m.movement_type] ?? m.movement_type} · {m.quantity >= 0 ? "+" : ""}{m.quantity} · balance {m.balance_after}
                </p>
                {m.reference && <p className="text-muted-foreground text-xs">Reference: {m.reference}</p>}
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <p>{m.performed_by_name ?? "-"}</p>
                <p>{formatDateTime(m.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
