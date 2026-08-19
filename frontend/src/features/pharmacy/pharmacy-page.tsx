import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Package, PackagePlus, Pill, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Medicine, MedicineCategory, MedicineStockMovement, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { formatCurrency, formatDate, formatDateTime, titleCase } from "@/lib/utils";
import { MOVEMENT_TYPE_LABELS } from "@/lib/constants";

function StockInDialog({ medicine }: { medicine: Medicine }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [batchNumber, setBatchNumber] = useState("");
  const [quantity, setQuantity] = useState("");
  const [purchasePrice, setPurchasePrice] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [supplier, setSupplier] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/pharmacy/medicines/${medicine.id}/stock_in/`, {
        batch_number: batchNumber,
        quantity: Number(quantity),
        purchase_price: purchasePrice || undefined,
        expiry_date: expiryDate || undefined,
        supplier,
      }),
    onSuccess: () => {
      success("Stock received");
      setOpen(false);
      setBatchNumber("");
      setQuantity("");
      setPurchasePrice("");
      setExpiryDate("");
      setSupplier("");
      queryClient.invalidateQueries({ queryKey: ["pharmacy"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to receive stock.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
          <PackagePlus /> Receive stock
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Receive stock — {medicine.name}</DialogTitle>
          <DialogDescription>Current stock: {medicine.total_stock} {medicine.unit}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>
                Batch number <span className="text-red-500">*</span>
              </Label>
              <Input value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} placeholder="e.g. BATCH-2026-01" />
            </div>
            <div className="space-y-2">
              <Label>
                Quantity <span className="text-red-500">*</span>
              </Label>
              <Input type="number" min={1} value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Purchase price</Label>
              <Input type="number" step="0.01" value={purchasePrice} onChange={(e) => setPurchasePrice(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Expiry date</Label>
              <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Supplier</Label>
            <Input value={supplier} onChange={(e) => setSupplier(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!batchNumber || !quantity || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Receive stock
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NewMedicineDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [genericName, setGenericName] = useState("");
  const [brandName, setBrandName] = useState("");
  const [category, setCategory] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [unit, setUnit] = useState("");
  const [strength, setStrength] = useState("");
  const [reorderLevel, setReorderLevel] = useState("");
  const [purchasePrice, setPurchasePrice] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const [requiresPrescription, setRequiresPrescription] = useState(false);
  const [batchNumber, setBatchNumber] = useState("");
  const [batchQuantity, setBatchQuantity] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [batchSupplier, setBatchSupplier] = useState("");

  const { data: categories } = useQuery({
    queryKey: ["pharmacy", "categories"],
    queryFn: () => api.get<MedicineCategory[]>("/pharmacy/categories/").then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/pharmacy/medicines/", {
        name,
        generic_name: genericName,
        brand_name: brandName,
        category: category ? Number(category) : null,
        manufacturer,
        unit,
        strength,
        reorder_level: reorderLevel ? Number(reorderLevel) : 0,
        purchase_price: purchasePrice,
        selling_price: sellingPrice,
        requires_prescription: requiresPrescription,
        initial_batch_number: batchNumber || undefined,
        initial_quantity: batchQuantity ? Number(batchQuantity) : undefined,
        initial_expiry_date: expiryDate || undefined,
        initial_supplier: batchSupplier || undefined,
        initial_purchase_price: purchasePrice || undefined,
      }),
    onSuccess: () => {
      success("Medicine added");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["pharmacy"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to add medicine.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Add medicine
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add medicine</DialogTitle>
          <DialogDescription>Add a new medicine to the pharmacy catalogue.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>
                Name <span className="text-red-500">*</span>
              </Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Strength</Label>
              <Input value={strength} onChange={(e) => setStrength(e.target.value)} placeholder="500mg" />
            </div>
            <div className="space-y-2">
              <Label>Generic name</Label>
              <Input value={genericName} onChange={(e) => setGenericName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Brand name</Label>
              <Input value={brandName} onChange={(e) => setBrandName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {(categories ?? []).map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Manufacturer</Label>
              <Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Unit</Label>
              <Input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="tablet" />
            </div>
            <div className="space-y-2">
              <Label>Reorder level</Label>
              <Input type="number" value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Purchase price</Label>
              <Input type="number" step="0.01" value={purchasePrice} onChange={(e) => setPurchasePrice(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Selling price</Label>
              <Input type="number" step="0.01" value={sellingPrice} onChange={(e) => setSellingPrice(e.target.value)} />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={requiresPrescription}
              onChange={(e) => setRequiresPrescription(e.target.checked)}
              className="size-4"
            />
            Requires prescription
          </label>
          <div className="rounded-md border bg-muted/30 p-3 space-y-3">
            <p className="text-sm font-medium">Initial Stock (optional)</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Batch number</Label>
                <Input value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} placeholder="e.g. BATCH-2026-01" />
              </div>
              <div className="space-y-2">
                <Label>Quantity</Label>
                <Input type="number" min={1} value={batchQuantity} onChange={(e) => setBatchQuantity(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Expiry date</Label>
                <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Supplier</Label>
                <Input value={batchSupplier} onChange={(e) => setBatchSupplier(e.target.value)} />
              </div>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Add medicine
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function PharmacyPage() {
  const { can } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["pharmacy", "medicines", params],
    queryFn: () => api.get<Paginated<Medicine>>("/pharmacy/medicines/", { params }).then((r) => r.data),
  });

  const { data: lowStock } = useQuery({
    queryKey: ["pharmacy", "low-stock"],
    queryFn: () => api.get<Medicine[]>("/pharmacy/medicines/low_stock/").then((r) => r.data),
  });

  const { data: movements } = useQuery({
    queryKey: ["pharmacy", "movements"],
    queryFn: () => api.get<MedicineStockMovement[]>("/pharmacy/medicines/stock_movements/").then((r) => r.data),
  });

  const columns: ColumnDef<Medicine>[] = [
    {
      header: "Medicine",
      cell: (m) => (
        <div>
          <p className="font-medium">
            {m.name} {m.strength ? `(${m.strength})` : ""}
          </p>
          <p className="text-muted-foreground text-xs">
            {m.generic_name || m.brand_name || m.category_name || "—"}
          </p>
        </div>
      ),
    },
    {
      header: "Stock",
      cell: (m) => (
        <div className="flex items-center gap-2">
          <span className={m.is_low_stock ? "font-semibold text-destructive" : "font-semibold"}>
            {m.total_stock} {m.unit}
          </span>
          {m.is_low_stock && <Badge variant="danger">Low</Badge>}
        </div>
      ),
    },
    {
      header: "Reorder level",
      cell: (m) => `${m.reorder_level} ${m.unit}`,
    },
    { header: "Selling price", cell: (m) => formatCurrency(m.selling_price) },
    {
      header: "Expiry",
      cell: (m) => (
        <div>
          <p>{m.earliest_expiry ? formatDate(m.earliest_expiry) : "—"}</p>
          {m.requires_prescription && <Badge variant="secondary">Rx</Badge>}
        </div>
      ),
    },
    {
      header: "",
      className: "text-right",
      cell: (m) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              Actions
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{m.name}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {can("pharmacy.view") && <StockInDialog medicine={m} />}
            <DropdownMenuItem asChild>
              <Link to="/pharmacy/dispense">Open dispense</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Pharmacy" description={`${data?.count?.toLocaleString() ?? 0} medicines in catalogue`}>
        <Button variant="outline" asChild>
          <Link to="/pharmacy/dispense">
            <Pill /> Dispense
          </Link>
        </Button>
        {can("pharmacy.view") && <NewMedicineDialog />}
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Pill} title="Medicines" value={data?.count ?? 0} tone="teal" />
        <StatCard icon={Package} title="Low stock" value={lowStock?.length ?? 0} tone="red" />
        <StatCard icon={PackagePlus} title="Dispense queue" value={0} tone="amber" hint="Open dispense screen" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <DataTable
            columns={columns}
            data={data?.results ?? []}
            loading={isLoading}
            error={isError ? "Unable to load medicines." : null}
            onRetry={refetch}
            count={data?.count}
            page={data?.page ?? page}
            totalPages={data?.total_pages ?? 1}
            onPageChange={setPage}
            toolbar={<SearchInput value={search} onChange={setSearch} placeholder="Search medicines…" className="sm:max-w-xs" />}
          />
        </div>
        <div>
          <div className="rounded-lg border bg-card">
            <div className="border-b px-4 py-3">
              <h3 className="text-sm font-semibold">Recent stock movements</h3>
            </div>
            <div className="divide-y">
              {(movements ?? []).slice(0, 10).map((mv) => (
                <div key={mv.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{mv.medicine_name}</p>
                    <p className="text-muted-foreground text-xs">
                      {MOVEMENT_TYPE_LABELS[mv.movement_type] ?? titleCase(mv.movement_type)} · {formatDateTime(mv.created_at)}
                    </p>
                  </div>
                  <span className={mv.quantity > 0 ? "font-semibold text-emerald-600" : "font-semibold text-destructive"}>
                    {mv.quantity > 0 ? `+${mv.quantity}` : mv.quantity}
                  </span>
                </div>
              ))}
              {(!movements || movements.length === 0) && (
                <p className="text-muted-foreground px-4 py-6 text-center text-sm">No movements recorded.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
