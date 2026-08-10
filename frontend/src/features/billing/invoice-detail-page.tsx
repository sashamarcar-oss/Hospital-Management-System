import { useState } from "react";
import { ArrowLeft, Banknote, Loader2, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, getErrorMessage } from "@/lib/api";
import type { Invoice } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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

export function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const { data: invoice, isLoading } = useQuery({
    queryKey: ["invoices", id],
    queryFn: () => api.get<Invoice>(`/billing/${id}/`).then((r) => r.data),
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.post(`/billing/${id}/cancel/`),
    onSuccess: () => {
      success("Invoice cancelled");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to cancel invoice.")),
  });

  if (isLoading) return <Skeleton className="h-60" />;
  if (!invoice) return <p className="text-muted-foreground py-10 text-center">Invoice not found.</p>;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Invoice ${invoice.invoice_number}`}
        description={`${invoice.patient_details?.full_name} — issued ${formatDateTime(invoice.issued_at)}`}
      >
        <Button variant="outline" onClick={() => navigate("/billing")}>
          <ArrowLeft /> Back
        </Button>
        {invoice.status !== "cancelled" && (
          <Button variant="destructive" onClick={() => cancelMutation.mutate()} disabled={cancelMutation.isPending}>
            <XCircle /> Cancel invoice
          </Button>
        )}
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Invoice items</CardTitle>
              <CardDescription>
                <StatusBadge value={invoice.status} labels={INVOICE_STATUS_LABELS} variants={INVOICE_STATUS_VARIANTS} />
              </CardDescription>
            </CardHeader>
            <CardContent>
              {invoice.items.length === 0 ? (
                <p className="text-muted-foreground text-sm">No items on this invoice yet.</p>
              ) : (
                <div className="divide-y rounded-lg border">
                  {invoice.items.map((item) => (
                    <div key={item.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                      <div>
                        <p className="font-medium">{item.description}</p>
                        <p className="text-muted-foreground text-xs">
                          {item.quantity} × {formatCurrency(item.unit_price)}
                        </p>
                      </div>
                      <p className="font-medium">{formatCurrency(item.line_total)}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Payments</CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.payments.length === 0 ? (
                <p className="text-muted-foreground text-sm">No payments received.</p>
              ) : (
                <div className="divide-y rounded-lg border">
                  {invoice.payments.map((p) => (
                    <div key={p.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                      <div>
                        <p className="font-medium">
                          {p.receipt_number} · {PAYMENT_METHOD_LABELS[p.method] ?? p.method}
                        </p>
                        <p className="text-muted-foreground text-xs">
                          {formatDateTime(p.paid_at)} · {p.received_by_name ?? "-"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(p.amount)}</p>
                        <p className="text-muted-foreground text-xs">{p.status}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Subtotal</span>
                <span>{formatCurrency(invoice.subtotal)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Discount</span>
                <span>-{formatCurrency(invoice.discount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tax ({invoice.tax_rate}%)</span>
                <span>{formatCurrency(invoice.tax)}</span>
              </div>
              <div className="flex justify-between border-t pt-2 font-medium">
                <span>Total</span>
                <span>{formatCurrency(invoice.total)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Paid</span>
                <span>{formatCurrency(invoice.amount_paid)}</span>
              </div>
              <div className="flex justify-between font-medium">
                <span>Balance</span>
                <span>{formatCurrency(invoice.balance)}</span>
              </div>
              {invoice.due_date && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Due</span>
                  <span>{invoice.due_date}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {Number(invoice.balance) > 0 && invoice.status !== "cancelled" && <AddPaymentDialog invoice={invoice} />}
        </div>
      </div>
    </div>
  );
}

function AddPaymentDialog({ invoice }: { invoice: Invoice }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState(String(invoice.balance));
  const [method, setMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/billing/payments/", {
        invoice: invoice.id,
        amount: Number(amount),
        method,
        reference,
        notes,
      }),
    onSuccess: () => {
      success("Payment recorded");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to record payment.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button className="w-full">
          <Banknote /> Record payment
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Record payment</DialogTitle>
          <DialogDescription>
            Outstanding balance: {formatCurrency(invoice.balance)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Amount</Label>
            <Input type="number" min={0.01} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Method</Label>
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(PAYMENT_METHOD_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Reference</Label>
            <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Optional" />
          </div>
          <div className="space-y-2">
            <Label>Notes</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!Number(amount) || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Banknote /> Record
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
