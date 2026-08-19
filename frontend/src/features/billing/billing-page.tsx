import { useState } from "react";
import { Banknote, Loader2, Plus, Receipt, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, getErrorMessage } from "@/lib/api";
import type { ChargeType, Invoice, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { PatientSelect } from "@/components/common/patient-select";
import { StatusBadge } from "@/components/common/status-badge";
import { StatCard } from "@/components/common/stat-card";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
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
import { useToast } from "@/hooks/use-toast";
import {
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_VARIANTS,
  PAYMENT_METHOD_LABELS,
} from "@/lib/constants";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export function BillingPage() {
  const { success, error } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("unpaid");
  const [search, setSearch] = useState("");

  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices", status, search],
    queryFn: () =>
      api
        .get<Paginated<Invoice>>("/billing/", {
          params: { status, search: search || undefined, page_size: 100 },
        })
        .then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ["invoices", "summary"],
    queryFn: () =>
      api
        .get<{ total_revenue: number | null; total_paid: number | null; outstanding: number | null }>(
          "/billing/summary/"
        )
        .then((r) => r.data),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => api.post(`/billing/${id}/cancel/`),
    onSuccess: () => {
      success("Invoice cancelled");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to cancel invoice.")),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Billing" description="Invoices, payments and outstanding balances.">
        <NewInvoiceDialog />
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={Receipt}
          title="Total revenue"
          value={formatCurrency(summary?.total_revenue ?? 0)}
        />
        <StatCard
          icon={Banknote}
          title="Collected"
          value={formatCurrency(summary?.total_paid ?? 0)}
        />
        <StatCard
          icon={XCircle}
          title="Outstanding"
          value={formatCurrency(summary?.outstanding ?? 0)}
        />
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unpaid">Unpaid</SelectItem>
                <SelectItem value="partially_paid">Partially paid</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="overdue">Overdue</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
                <SelectItem value="all">All</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Search invoice or patient..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-xs"
            />
          </div>

          {isLoading ? (
            <Skeleton className="h-40" />
          ) : (invoices?.results ?? []).length === 0 ? (
            <p className="text-muted-foreground py-10 text-center text-sm">No invoices found.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left font-medium">Invoice</th>
                    <th className="p-3 text-left font-medium">Patient</th>
                    <th className="p-3 text-left font-medium">Status</th>
                    <th className="p-3 text-right font-medium">Total</th>
                    <th className="p-3 text-right font-medium">Balance</th>
                    <th className="p-3 text-left font-medium">Issued</th>
                    <th className="p-3 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(invoices?.results ?? []).map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => navigate(`/billing/${inv.id}`)}
                      className="cursor-pointer transition-colors hover:bg-muted/40"
                    >
                      <td className="p-3 font-medium">{inv.invoice_number}</td>
                      <td className="p-3">{inv.patient_details?.full_name}</td>
                      <td className="p-3">
                        <StatusBadge
                          value={inv.status}
                          labels={INVOICE_STATUS_LABELS}
                          variants={INVOICE_STATUS_VARIANTS}
                        />
                      </td>
                      <td className="p-3 text-right">{formatCurrency(inv.total)}</td>
                      <td className="p-3 text-right">{formatCurrency(inv.balance)}</td>
                      <td className="p-3 text-muted-foreground">{formatDateTime(inv.issued_at)}</td>
                      <td className="p-3 text-right" onClick={(e) => e.stopPropagation()}>
                        {inv.status !== "cancelled" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => cancelMutation.mutate(inv.id)}
                          >
                            <XCircle /> Cancel
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function NewInvoiceDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [patient, setPatient] = useState<number | null>(null);
  const [taxRate, setTaxRate] = useState("");
  const [discount, setDiscount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<{ description: string; quantity: number; unit_price: number; charge_type: number | null }[]>([]);

  const { data: chargeTypes } = useQuery({
    queryKey: ["charge-types"],
    queryFn: () => api.get<ChargeType[]>("/billing/charge-types/").then((r) => r.data),
  });

  const addItem = (chargeType?: ChargeType) => {
    setItems((prev) => [
      ...prev,
      {
        description: chargeType?.name ?? "",
        quantity: 1,
        unit_price: chargeType ? Number(chargeType.default_price) : 0,
        charge_type: chargeType?.id ?? null,
      },
    ]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const updateItem = (index: number, field: string, value: string | number) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
  };

  const subtotal = items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);
  const taxAmount = subtotal * ((Number(taxRate) || 0) / 100);
  const total = Math.max(0, subtotal - (Number(discount) || 0) + taxAmount);

  const resetForm = () => {
    setPatient(null);
    setTaxRate("");
    setDiscount("");
    setDueDate("");
    setNotes("");
    setItems([]);
  };

  const mutation = useMutation({
    mutationFn: async () => {
      if (items.length === 0) throw new Error("Add at least one billable item before creating an invoice.");
      return api.post("/billing/", {
        patient,
        discount: Number(discount) || 0,
        tax_rate: Number(taxRate) || 0,
        due_date: dueDate || null,
        notes,
        items: items.map((item) => ({
          description: item.description,
          quantity: item.quantity,
          unit_price: Number(item.unit_price.toFixed(2)),
          charge_type: item.charge_type,
        })),
      });
    },
    onSuccess: () => {
      success("Invoice created", "The invoice has been created with the specified line items.");
      setOpen(false);
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create invoice.")),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New invoice
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create invoice</DialogTitle>
          <DialogDescription>Select a patient and add billable items.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Invoice Items</Label>
              <div className="flex gap-2">
                {(chargeTypes ?? []).length > 0 && (
                  <Select onValueChange={(id) => {
                    const ct = chargeTypes?.find((c) => c.id === Number(id));
                    if (ct) addItem(ct);
                  }}>
                    <SelectTrigger className="h-8 w-auto text-xs">
                      <SelectValue placeholder="Add from catalog" />
                    </SelectTrigger>
                    <SelectContent>
                      {chargeTypes?.map((ct) => (
                        <SelectItem key={ct.id} value={String(ct.id)}>
                          {ct.name} — {formatCurrency(ct.default_price)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                <Button type="button" size="sm" variant="outline" onClick={() => addItem()}>
                  <Plus className="size-3" /> Custom
                </Button>
              </div>
            </div>

            {items.length === 0 ? (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                <p>No items added yet.</p>
                <p className="text-xs mt-1">Select a service from the catalog or add a custom item.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {items.map((item, index) => (
                  <div key={index} className="grid grid-cols-[1fr_80px_120px_120px_32px] items-end gap-2 rounded-lg border p-2">
                    <div className="space-y-1">
                      <Label className="text-xs">Description</Label>
                      <Input
                        value={item.description}
                        onChange={(e) => updateItem(index, "description", e.target.value)}
                        placeholder="Service description"
                        className="h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Qty</Label>
                      <Input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(e) => updateItem(index, "quantity", parseInt(e.target.value) || 1)}
                        className="h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Unit Price (KES)</Label>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => updateItem(index, "unit_price", parseFloat(e.target.value) || 0)}
                        className="h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Subtotal</Label>
                      <div className="flex h-8 items-center px-3 text-sm font-medium">
                        {formatCurrency(item.quantity * item.unit_price)}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeItem(index)}
                      className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                    >
                      <XCircle className="size-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {items.length > 0 && (
            <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Subtotal</span>
                <span className="font-medium">{formatCurrency(subtotal)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Discount (KES)</span>
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  className="h-8 w-28 text-right"
                  placeholder="0"
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Tax rate (%)</span>
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  value={taxRate}
                  onChange={(e) => setTaxRate(e.target.value)}
                  className="h-8 w-28 text-right"
                  placeholder="0"
                />
              </div>
              {Number(taxRate) > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tax</span>
                  <span>{formatCurrency(taxAmount)}</span>
                </div>
              )}
              <div className="flex justify-between border-t pt-2 text-base font-medium">
                <span>Total</span>
                <span>{formatCurrency(total)}</span>
              </div>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Due date</Label>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!patient || items.length === 0 || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Receipt /> Create invoice
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
