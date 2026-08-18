import { useState, useCallback } from "react";
import {
  Banknote,
  CreditCard,
  Download,
  Eye,
  Filter,
  Loader2,
  Phone,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Wallet,
  X,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, downloadFile, getErrorMessage } from "@/lib/api";
import type { Invoice, Paginated, Payment, PaymentStats, PatientSummary } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { PatientSelect } from "@/components/common/patient-select";
import { StatusBadge } from "@/components/common/status-badge";
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
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import {
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_VARIANTS,
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS_LABELS,
  PAYMENT_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export function PaymentsPage() {
  const { can } = useAuth();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [detailPayment, setDetailPayment] = useState<Payment | null>(null);
  const [showReceivePayment, setShowReceivePayment] = useState(false);

  const params: Record<string, string> = {
    search: search || undefined,
    page_size: "100",
    ordering: "-paid_at",
  };
  if (statusFilter !== "all") params.status = statusFilter;
  if (methodFilter !== "all") params.method = methodFilter;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;

  const { data: payments, isLoading } = useQuery({
    queryKey: ["payments", search, statusFilter, methodFilter, dateFrom, dateTo],
    queryFn: () => api.get<Paginated<Payment>>("/billing/payments/", { params }).then((r) => r.data),
  });

  const { data: stats } = useQuery({
    queryKey: ["payments", "stats"],
    queryFn: () => api.get<PaymentStats>("/billing/payments/stats/").then((r) => r.data),
  });

  const rows = payments?.results ?? [];
  const hasFilters = statusFilter !== "all" || methodFilter !== "all" || dateFrom || dateTo;

  const clearFilters = () => {
    setStatusFilter("all");
    setMethodFilter("all");
    setDateFrom("");
    setDateTo("");
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Payments" description="All received payments and their transaction details.">
        {can("payments.receive_payment") && (
          <Button onClick={() => setShowReceivePayment(true)}>
            <Plus /> Receive Payment
          </Button>
        )}
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          icon={Banknote}
          title="Today's Collection"
          value={formatCurrency(stats?.today_collection ?? 0)}
          tone="emerald"
        />
        <StatCard
          icon={Wallet}
          title="Total Payments"
          value={formatCurrency(stats?.total_payments ?? 0)}
          hint={`${stats?.total_count ?? 0} transactions`}
          tone="teal"
        />
        <StatCard
          icon={Phone}
          title="M-Pesa Collection"
          value={formatCurrency(stats?.mpesa_collection ?? 0)}
          tone="blue"
        />
        <StatCard
          icon={CreditCard}
          title="Cash Collection"
          value={formatCurrency(stats?.cash_collection ?? 0)}
          tone="amber"
        />
        <StatCard
          icon={RefreshCw}
          title="Outstanding Balance"
          value={formatCurrency(stats?.outstanding_balance ?? 0)}
          tone="red"
        />
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
              <Input
                className="pl-8"
                placeholder="Search by Payment ID, receipt, patient, invoice, reference..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            <Button variant={showFilters ? "default" : "outline"} size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Filter /> Filters {hasFilters && <span className="ml-1 rounded-full bg-primary-foreground px-1.5 text-xs text-primary">!</span>}
            </Button>
          </div>

          {showFilters && (
            <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border bg-muted/30 p-3">
              <div className="space-y-1">
                <Label className="text-xs">Status</Label>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="refunded">Refunded</SelectItem>
                    <SelectItem value="reversed">Reversed</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Payment Method</Label>
                <Select value={methodFilter} onValueChange={setMethodFilter}>
                  <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Methods</SelectItem>
                    {Object.entries(PAYMENT_METHOD_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">From</Label>
                <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-40" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">To</Label>
                <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-40" />
              </div>
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="size-4" /> Clear
                </Button>
              )}
            </div>
          )}

          {isLoading ? (
            <Skeleton className="h-40" />
          ) : rows.length === 0 ? (
            <p className="text-muted-foreground py-10 text-center text-sm">No payments found.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[1200px] text-sm">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left font-medium">Payment ID</th>
                    <th className="p-3 text-left font-medium">Patient</th>
                    <th className="p-3 text-left font-medium">Invoice</th>
                    <th className="p-3 text-right font-medium">Amount</th>
                    <th className="p-3 text-left font-medium">Method</th>
                    <th className="p-3 text-left font-medium">Reference</th>
                    <th className="p-3 text-left font-medium">Date</th>
                    <th className="p-3 text-left font-medium">Received By</th>
                    <th className="p-3 text-left font-medium">Status</th>
                    <th className="p-3 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rows.map((payment) => (
                    <tr key={payment.id} className="hover:bg-muted/40">
                      <td className="p-3 font-medium">{payment.payment_number || payment.receipt_number}</td>
                      <td className="p-3">{payment.patient_details?.full_name ?? "-"}</td>
                      <td className="p-3">{payment.invoice_number || `#${payment.invoice}`}</td>
                      <td className="p-3 text-right">{formatCurrency(payment.amount)}</td>
                      <td className="p-3">{PAYMENT_METHOD_LABELS[payment.method] ?? payment.method}</td>
                      <td className="p-3">{payment.reference || payment.mpesa_transaction_code || "-"}</td>
                      <td className="p-3 whitespace-nowrap">{formatDateTime(payment.paid_at)}</td>
                      <td className="p-3">{payment.received_by_name || "-"}</td>
                      <td className="p-3">
                        <StatusBadge value={payment.status} labels={PAYMENT_STATUS_LABELS} variants={PAYMENT_STATUS_VARIANTS} />
                      </td>
                      <td className="p-3 text-right">
                        <Button variant="ghost" size="sm" onClick={() => setDetailPayment(payment)}>
                          <Eye className="size-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {showReceivePayment && (
        <ReceivePaymentDialog open={showReceivePayment} onClose={() => setShowReceivePayment(false)} />
      )}

      {detailPayment && (
        <PaymentDetailDialog payment={detailPayment} open={!!detailPayment} onClose={() => setDetailPayment(null)} />
      )}
    </div>
  );
}

function ReceivePaymentDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [patient, setPatient] = useState<number | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");
  const [insuranceProvider, setInsuranceProvider] = useState("");
  const [policyNumber, setPolicyNumber] = useState("");
  const [insuranceAmount, setInsuranceAmount] = useState("");
  const [patientCopay, setPatientCopay] = useState("");
  const [mpesaPhone, setMpesaPhone] = useState("");
  const [mpesaCode, setMpesaCode] = useState("");

  const { data: patientInvoices, isLoading: loadingInvoices } = useQuery({
    queryKey: ["patient-invoices", patient],
    queryFn: () =>
      api.get<Paginated<Invoice>>("/billing/", {
        params: { patient_id: patient, page_size: 50 },
      }).then((r) => r.data),
    enabled: !!patient,
  });

  const invoices = (patientInvoices?.results ?? []).filter(
    (inv) => Number(inv.balance) > 0 && inv.status !== "cancelled"
  );

  const mutation = useMutation({
    mutationFn: () => {
      const data: Record<string, unknown> = {
        invoice: selectedInvoice!.id,
        amount: Number(amount),
        method,
        reference: reference || undefined,
        notes: notes || undefined,
      };
      if (method === "mpesa") {
        data.mpesa_phone = mpesaPhone;
        data.mpesa_transaction_code = mpesaCode;
        data.reference = mpesaCode;
      }
      if (method === "insurance") {
        data.insurance_provider = insuranceProvider;
        data.policy_number = policyNumber;
        data.insurance_amount = Number(insuranceAmount) || 0;
        data.patient_copay = Number(patientCopay) || 0;
      }
      return api.post("/billing/payments/", data);
    },
    onSuccess: (res) => {
      success("Payment recorded", `Payment ${res.data.payment_number} created successfully.`);
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      resetForm();
      onClose();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to record payment.")),
  });

  const resetForm = () => {
    setPatient(null);
    setSelectedInvoice(null);
    setAmount("");
    setMethod("cash");
    setReference("");
    setNotes("");
    setInsuranceProvider("");
    setPolicyNumber("");
    setInsuranceAmount("");
    setPatientCopay("");
    setMpesaPhone("");
    setMpesaCode("");
  };

  const outstandingBalance = selectedInvoice ? Number(selectedInvoice.balance) : 0;
  const paymentAmount = Number(amount) || 0;
  const remainingAfterPayment = outstandingBalance - paymentAmount;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Receive Payment</DialogTitle>
          <DialogDescription>Select a patient and invoice, then enter payment details.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={(id) => { setPatient(id); setSelectedInvoice(null); setAmount(""); }} />
          </div>

          {patient && (
            <div className="space-y-2">
              <Label>Outstanding Invoices</Label>
              {loadingInvoices ? (
                <Skeleton className="h-20" />
              ) : invoices.length === 0 ? (
                <p className="text-muted-foreground rounded-lg border p-4 text-center text-sm">No outstanding invoices for this patient.</p>
              ) : (
                <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border p-2">
                  {invoices.map((inv) => (
                    <button
                      key={inv.id}
                      type="button"
                      onClick={() => { setSelectedInvoice(inv); setAmount(String(inv.balance)); }}
                      className={`w-full rounded-lg border p-3 text-left text-sm transition-colors ${
                        selectedInvoice?.id === inv.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{inv.invoice_number}</span>
                        <StatusBadge value={inv.status} labels={INVOICE_STATUS_LABELS} variants={INVOICE_STATUS_VARIANTS} />
                      </div>
                      <div className="mt-1 flex gap-4 text-muted-foreground text-xs">
                        <span>Total: {formatCurrency(inv.total)}</span>
                        <span>Paid: {formatCurrency(inv.amount_paid)}</span>
                        <span className="font-medium text-foreground">Balance: {formatCurrency(inv.balance)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {selectedInvoice && (
            <div className="rounded-lg border bg-muted/30 p-3">
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div><span className="text-muted-foreground">Invoice Total:</span> <span className="font-medium">{formatCurrency(selectedInvoice.total)}</span></div>
                <div><span className="text-muted-foreground">Already Paid:</span> <span className="font-medium">{formatCurrency(selectedInvoice.amount_paid)}</span></div>
                <div><span className="text-muted-foreground">Outstanding:</span> <span className="font-medium text-destructive">{formatCurrency(selectedInvoice.balance)}</span></div>
              </div>
            </div>
          )}

          {selectedInvoice && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Amount to Pay (KES)</Label>
                  <Input type="number" min={0.01} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" />
                  {paymentAmount > 0 && (
                    <p className={`text-xs ${remainingAfterPayment <= 0 ? "text-green-600" : "text-muted-foreground"}`}>
                      Remaining after payment: {formatCurrency(Math.max(0, remainingAfterPayment))}
                      {remainingAfterPayment <= 0 && " (Fully paid)"}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>Payment Method</Label>
                  <Select value={method} onValueChange={setMethod}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(PAYMENT_METHOD_LABELS).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Payment Date</Label>
                <Input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
              </div>

              {method === "mpesa" && (
                <div className="space-y-3 rounded-lg border bg-muted/30 p-3">
                  <p className="text-sm font-medium">M-Pesa Details</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1"><Label>Phone Number</Label><Input value={mpesaPhone} onChange={(e) => setMpesaPhone(e.target.value)} placeholder="07XXXXXXXX" /></div>
                    <div className="space-y-1"><Label>M-Pesa Transaction Code</Label><Input value={mpesaCode} onChange={(e) => { setMpesaCode(e.target.value); setReference(e.target.value); }} placeholder="e.g. QWE123ABC" /></div>
                  </div>
                </div>
              )}

              {method === "insurance" && (
                <div className="space-y-3 rounded-lg border bg-muted/30 p-3">
                  <p className="text-sm font-medium">Insurance Details</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1"><Label>Provider</Label><Input value={insuranceProvider} onChange={(e) => setInsuranceProvider(e.target.value)} placeholder="Insurer name" /></div>
                    <div className="space-y-1"><Label>Policy Number</Label><Input value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} /></div>
                    <div className="space-y-1"><Label>Insurance Amount</Label><Input type="number" min={0} value={insuranceAmount} onChange={(e) => setInsuranceAmount(e.target.value)} /></div>
                    <div className="space-y-1"><Label>Patient Co-pay</Label><Input type="number" min={0} value={patientCopay} onChange={(e) => setPatientCopay(e.target.value)} /></div>
                  </div>
                </div>
              )}

              {method !== "mpesa" && method !== "insurance" && (
                <div className="space-y-2">
                  <Label>Transaction Reference</Label>
                  <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Optional" />
                </div>
              )}

              <div className="space-y-2">
                <Label>Notes</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!selectedInvoice || !paymentAmount || paymentAmount <= 0 || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Banknote /> Record Payment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PaymentDetailDialog({ payment, open, onClose }: { payment: Payment; open: boolean; onClose: () => void }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const [showRefundDialog, setShowRefundDialog] = useState(false);
  const [showReverseDialog, setShowReverseDialog] = useState(false);

  const reverseMutation = useMutation({
    mutationFn: (reason: string) => api.post(`/billing/payments/${payment.id}/reverse/`, { reason }),
    onSuccess: () => {
      success("Payment reversed");
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setShowReverseDialog(false);
      onClose();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to reverse payment.")),
  });

  const handleDownloadReceipt = async () => {
    try {
      await downloadFile(`/billing/payments/${payment.id}/receipt-pdf/`, `${payment.receipt_number}.pdf`);
    } catch {
      error("Unable to download receipt.");
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Payment Details</DialogTitle>
            <DialogDescription>{payment.payment_number}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <DetailRow label="Payment ID" value={payment.payment_number} />
              <DetailRow label="Receipt Number" value={payment.receipt_number} />
              <DetailRow label="Patient" value={payment.patient_details?.full_name} />
              <DetailRow label="Patient Number" value={payment.patient_details?.patient_number} />
              <DetailRow label="Invoice Number" value={payment.invoice_number} />
              <DetailRow label="Amount Paid" value={formatCurrency(payment.amount)} bold />
              <DetailRow label="Payment Method" value={PAYMENT_METHOD_LABELS[payment.method] ?? payment.method} />
              <DetailRow label="Reference" value={payment.reference || payment.mpesa_transaction_code || "-"} />
              <DetailRow label="Payment Date" value={formatDateTime(payment.paid_at)} />
              <DetailRow label="Received By" value={payment.received_by_name || "-"} />
              <DetailRow label="Status" value={
                <StatusBadge value={payment.status} labels={PAYMENT_STATUS_LABELS} variants={PAYMENT_STATUS_VARIANTS} />
              } />
            </div>

            {payment.mpesa_phone && (
              <div className="rounded-lg border bg-muted/30 p-2">
                <DetailRow label="M-Pesa Phone" value={payment.mpesa_phone} />
                <DetailRow label="M-Pesa Code" value={payment.mpesa_transaction_code} />
              </div>
            )}

            {payment.method === "insurance" && (
              <div className="rounded-lg border bg-muted/30 p-2">
                <DetailRow label="Insurance Provider" value={payment.insurance_provider} />
                <DetailRow label="Policy Number" value={payment.policy_number} />
                <DetailRow label="Insurance Amount" value={formatCurrency(payment.insurance_amount)} />
                <DetailRow label="Patient Co-pay" value={formatCurrency(payment.patient_copay)} />
              </div>
            )}

            {payment.reverse_reason && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-2">
                <p className="mb-1 font-medium text-destructive text-xs">Reversal Info</p>
                <DetailRow label="Reason" value={payment.reverse_reason} />
                <DetailRow label="Reversed By" value={payment.reversed_by_name} />
                <DetailRow label="Reversed At" value={payment.reversed_at ? formatDateTime(payment.reversed_at) : "-"} />
              </div>
            )}

            {payment.refund_status && payment.refund_status !== "" && (
              <div className="rounded-lg border bg-muted/30 p-2">
                <p className="mb-1 font-medium text-xs">Refund Info</p>
                <DetailRow label="Refund Amount" value={formatCurrency(payment.refund_amount)} />
                <DetailRow label="Reason" value={payment.refund_reason || "-"} />
                <DetailRow label="Status" value={payment.refund_status} />
                {payment.refund_approved_by_name && <DetailRow label="Approved By" value={payment.refund_approved_by_name} />}
              </div>
            )}

            {payment.notes && (
              <div className="rounded-lg border bg-muted/30 p-2">
                <p className="mb-1 text-xs font-medium">Notes</p>
                <p className="text-muted-foreground">{payment.notes}</p>
              </div>
            )}
          </div>
          <DialogFooter className="flex-row flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => window.open(`/billing/${payment.invoice}`, "_blank")}>
              View Invoice
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadReceipt}>
              <Download className="size-4" /> Download Receipt
            </Button>
            {can("payments.receive_payment") && payment.status === "completed" && (
              <>
                <Button variant="outline" size="sm" onClick={() => setShowRefundDialog(true)}>
                  Refund
                </Button>
                {can("payments.reverse") && (
                  <Button variant="destructive" size="sm" onClick={() => setShowReverseDialog(true)}>
                    <RotateCcw className="size-4" /> Reverse
                  </Button>
                )}
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {showRefundDialog && (
        <RefundDialog payment={payment} open={showRefundDialog} onClose={() => setShowRefundDialog(false)} />
      )}

      {showReverseDialog && (
        <ReverseDialog payment={payment} open={showReverseDialog} onClose={() => setShowReverseDialog(false)}
          onConfirm={(reason) => reverseMutation.mutate(reason)} isPending={reverseMutation.isPending} />
      )}
    </>
  );
}

function DetailRow({ label, value, bold }: { label: string; value: React.ReactNode; bold?: boolean }) {
  return (
    <div className="flex justify-between gap-2 py-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className={bold ? "font-medium" : ""}>{value}</span>
    </div>
  );
}

function RefundDialog({ payment, open, onClose }: { payment: Payment; open: boolean; onClose: () => void }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState(String(payment.amount));
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.post(`/billing/payments/${payment.id}/refund/`, {
      amount: Number(amount),
      reason,
    }),
    onSuccess: () => {
      success("Refund requested", "Refund is pending approval.");
      queryClient.invalidateQueries({ queryKey: ["payments"] });
      onClose();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to request refund.")),
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Request Refund</DialogTitle>
          <DialogDescription>Max refund: {formatCurrency(payment.amount)}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Refund Amount</Label>
            <Input type="number" min={0.01} max={Number(payment.amount)} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Reason</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={!amount || !reason || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Submit Refund
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReverseDialog({ payment, open, onClose, onConfirm, isPending }: {
  payment: Payment; open: boolean; onClose: () => void; onConfirm: (reason: string) => void; isPending: boolean;
}) {
  const [reason, setReason] = useState("");

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Reverse Payment</DialogTitle>
          <DialogDescription>This will reverse payment {payment.payment_number} for {formatCurrency(payment.amount)}.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Reversal Reason</Label>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={() => onConfirm(reason)} disabled={!reason || isPending}>
            {isPending && <Loader2 className="animate-spin" />}
            Confirm Reversal
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
