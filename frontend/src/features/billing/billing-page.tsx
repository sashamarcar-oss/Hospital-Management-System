import { useState } from "react";
import { Banknote, Loader2, Plus, Receipt, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, getErrorMessage } from "@/lib/api";
import type { Invoice, Paginated } from "@/lib/types";
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
  const [discount, setDiscount] = useState("");
  const [taxRate, setTaxRate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/billing/", {
        patient,
        discount: discount ? Number(discount) : 0,
        tax_rate: taxRate ? Number(taxRate) : 0,
        due_date: dueDate || null,
        notes,
      }),
    onSuccess: () => {
      success("Invoice created", "Charge items can be added to it.");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create invoice.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New invoice
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create invoice</DialogTitle>
          <DialogDescription>Create an invoice for a patient. Charge items are added separately.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Discount</Label>
              <Input type="number" min={0} step="0.01" value={discount} onChange={(e) => setDiscount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <Label>Tax rate (%)</Label>
              <Input type="number" min={0} step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} placeholder="0" />
            </div>
            <div className="space-y-2">
              <Label>Due date</Label>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!patient || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Receipt /> Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
