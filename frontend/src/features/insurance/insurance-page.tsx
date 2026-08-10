import { useState } from "react";
import {
  Building2,
  CheckCircle2,
  FileText,
  Loader2,
  Plus,
  ShieldCheck,
  Send,
  Stethoscope,
  XCircle,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type {
  InsuranceClaim,
  InsurancePolicy,
  InsuranceProvider,
  Paginated,
} from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { PatientSelect } from "@/components/common/patient-select";
import { StatusBadge } from "@/components/common/status-badge";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  CLAIM_STATUS_LABELS,
  CLAIM_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/utils";

export function InsurancePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Insurance" description="Providers, policies and claims." />
      <Tabs defaultValue="claims">
        <TabsList>
          <TabsTrigger value="claims">Claims</TabsTrigger>
          <TabsTrigger value="policies">Policies</TabsTrigger>
          <TabsTrigger value="providers">Providers</TabsTrigger>
        </TabsList>
        <TabsContent value="claims">
          <ClaimsTab />
        </TabsContent>
        <TabsContent value="policies">
          <PoliciesTab />
        </TabsContent>
        <TabsContent value="providers">
          <ProvidersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ClaimsTab() {
  const { data: claims, isLoading } = useQuery({
    queryKey: ["insurance", "claims"],
    queryFn: () =>
      api
        .get<Paginated<InsuranceClaim>>("/insurance/claims/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <NewClaimDialog />
      </div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (claims?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No claims yet.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(claims?.results ?? []).map((c) => (
            <ClaimRow key={c.id} claim={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function ClaimRow({ claim }: { claim: InsuranceClaim }) {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["insurance"] });

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="font-medium">
          {claim.claim_number} · {claim.patient_details?.full_name}
        </p>
        <p className="text-muted-foreground text-xs">
          {claim.policy_details?.provider} · policy {claim.policy_details?.policy_number} · invoice{" "}
          {claim.invoice_number ?? "-"}
        </p>
        <p className="text-muted-foreground text-xs">
          Claimed {formatCurrency(claim.amount)} · approved{" "}
          {claim.approved_amount ? formatCurrency(claim.approved_amount) : "-"}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge value={claim.status} labels={CLAIM_STATUS_LABELS} variants={CLAIM_STATUS_VARIANTS} />
        <ClaimActions claim={claim} onDone={invalidate} />
      </div>
    </div>
  );
}

const CLAIM_FLOW = ["submit", "start_review", "approve", "partial_approve", "reject", "mark_paid"];

function ClaimActions({ claim, onDone }: { claim: InsuranceClaim; onDone: () => void }) {
  const { success, error } = useToast();
  const [approving, setApproving] = useState(false);
  const [approvedAmount, setApprovedAmount] = useState(claim.amount);
  const [rejectedAmount, setRejectedAmount] = useState("");
  const [contribution, setContribution] = useState("");

  const mutation = useMutation({
    mutationFn: (action: string) => {
      const payload: Record<string, unknown> = {};
      if (action === "approve" || action === "mark_paid") payload.approved_amount = Number(approvedAmount);
      if (action === "partial_approve") {
        payload.approved_amount = Number(approvedAmount);
        payload.rejected_amount = rejectedAmount ? Number(rejectedAmount) : null;
        payload.patient_contribution = contribution ? Number(contribution) : null;
      }
      return api.post(`/insurance/claims/${claim.id}/${action}/`, payload);
    },
    onSuccess: () => {
      success("Claim updated");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Action failed.")),
  });

  const run = (action: string) => mutation.mutate(action);

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {claim.status === "draft" && (
        <Button variant="outline" size="sm" onClick={() => run("submit")}>
          <Send /> Submit
        </Button>
      )}
      {claim.status === "submitted" && (
        <Button variant="outline" size="sm" onClick={() => run("start_review")}>
          <FileText /> Review
        </Button>
      )}
      {claim.status === "under_review" && (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              <CheckCircle2 /> Decide
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>Approve claim {claim.claim_number}</DialogTitle>
              <DialogDescription>Set the approved, rejected and patient contribution amounts.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Approved amount</Label>
                <Input type="number" min={0} step="0.01" value={approvedAmount} onChange={(e) => setApprovedAmount(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Rejected amount</Label>
                <Input type="number" min={0} step="0.01" value={rejectedAmount} onChange={(e) => setRejectedAmount(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Patient contribution</Label>
                <Input type="number" min={0} step="0.01" value={contribution} onChange={(e) => setContribution(e.target.value)} />
              </div>
            </div>
            <DialogFooter className="flex-col gap-2">
              <Button onClick={() => run("approve")} disabled={mutation.isPending}>
                {mutation.isPending && <Loader2 className="animate-spin" />} Approve in full
              </Button>
              <Button variant="outline" onClick={() => run("partial_approve")} disabled={mutation.isPending}>
                Partial approval
              </Button>
              <Button variant="destructive" onClick={() => run("reject")} disabled={mutation.isPending}>
                <XCircle /> Reject
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
      {claim.status === "approved" && (
        <Button variant="outline" size="sm" onClick={() => run("mark_paid")}>
          <CheckCircle2 /> Mark paid
        </Button>
      )}
      {claim.status === "partially_approved" && (
        <Button variant="outline" size="sm" onClick={() => run("mark_paid")}>
          <CheckCircle2 /> Mark paid
        </Button>
      )}
    </div>
  );
}

function NewClaimDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [patient, setPatient] = useState<number | null>(null);
  const [policy, setPolicy] = useState<string>("");
  const [invoice, setInvoice] = useState<string>("");
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");

  const { data: policies } = useQuery({
    queryKey: ["insurance", "policies", "options"],
    queryFn: () =>
      api.get<Paginated<InsurancePolicy>>("/insurance/policies/", { params: { page_size: 200 } }).then((r) => r.data),
  });
  const { data: invoices } = useQuery({
    queryKey: ["insurance", "invoices", "options"],
    queryFn: () => api.get<Paginated<{ id: number; invoice_number: string; balance: string }>>("/billing/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/insurance/claims/", {
        policy: Number(policy),
        patient,
        invoice: invoice ? Number(invoice) : null,
        amount: Number(amount),
        notes,
      }),
    onSuccess: () => {
      success("Claim created");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["insurance"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create claim.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New claim
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create insurance claim</DialogTitle>
          <DialogDescription>File a claim against a patient's policy.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>
          <div className="space-y-2">
            <Label>Policy</Label>
            <Select value={policy} onValueChange={setPolicy}>
              <SelectTrigger><SelectValue placeholder="Select policy" /></SelectTrigger>
              <SelectContent>
                {(policies?.results ?? []).map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.patient_details?.full_name} — {p.provider_name} ({p.policy_number})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Invoice (optional)</Label>
              <Select value={invoice} onValueChange={setInvoice}>
                <SelectTrigger><SelectValue placeholder="Select invoice" /></SelectTrigger>
                <SelectContent>
                  {(invoices?.results ?? []).map((i) => (
                    <SelectItem key={i.id} value={String(i.id)}>{i.invoice_number}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Claim amount</Label>
              <Input type="number" min={0} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!(patient && policy && amount) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <FileText /> Create claim
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PoliciesTab() {
  const { data: policies, isLoading } = useQuery({
    queryKey: ["insurance", "policies"],
    queryFn: () =>
      api
        .get<Paginated<InsurancePolicy>>("/insurance/policies/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <NewPolicyDialog />
      </div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (policies?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No policies.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(policies?.results ?? []).map((p) => (
            <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-medium">
                  {p.patient_details?.full_name} — {p.provider_name}
                </p>
                <p className="text-muted-foreground text-xs">
                  {p.policy_number} · {p.coverage_type} · limit {formatCurrency(p.coverage_limit)}
                </p>
                <p className="text-muted-foreground text-xs">
                  {formatDate(p.start_date)} → {p.end_date ? formatDate(p.end_date) : "open"}
                </p>
              </div>
              <span className="text-muted-foreground text-xs">{p.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewPolicyDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [patient, setPatient] = useState<number | null>(null);
  const [provider, setProvider] = useState<string>("");
  const [policyNumber, setPolicyNumber] = useState("");
  const [membershipNumber, setMembershipNumber] = useState("");
  const [coverageType, setCoverageType] = useState("inpatient");
  const [coverageLimit, setCoverageLimit] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const { data: providers } = useQuery({
    queryKey: ["insurance", "providers", "options"],
    queryFn: () =>
      api.get<Paginated<InsuranceProvider>>("/insurance/providers/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/insurance/policies/", {
        patient,
        provider: Number(provider),
        policy_number: policyNumber,
        membership_number: membershipNumber,
        coverage_type: coverageType,
        coverage_limit: coverageLimit ? Number(coverageLimit) : null,
        start_date: startDate,
        end_date: endDate || null,
      }),
    onSuccess: () => {
      success("Policy created");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["insurance"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create policy.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <ShieldCheck /> New policy
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Register insurance policy</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
              <SelectContent>
                {(providers?.results ?? []).map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Policy number</Label>
              <Input value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Membership number</Label>
              <Input value={membershipNumber} onChange={(e) => setMembershipNumber(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Coverage type</Label>
              <Select value={coverageType} onValueChange={setCoverageType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="inpatient">Inpatient</SelectItem>
                  <SelectItem value="outpatient">Outpatient</SelectItem>
                  <SelectItem value="comprehensive">Comprehensive</SelectItem>
                  <SelectItem value="dental">Dental</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Coverage limit</Label>
              <Input type="number" min={0} step="0.01" value={coverageLimit} onChange={(e) => setCoverageLimit(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Start date</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>End date (optional)</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!(patient && provider && policyNumber && startDate) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <ShieldCheck /> Save policy
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ProvidersTab() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");

  const { data: providers, isLoading } = useQuery({
    queryKey: ["insurance", "providers"],
    queryFn: () =>
      api
        .get<Paginated<InsuranceProvider>>("/insurance/providers/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/insurance/providers/", { name, code, phone, email, address }),
    onSuccess: () => {
      success("Provider added");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["insurance"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to add provider.")),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="outline">
              <Building2 /> Add provider
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>Add insurance provider</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Code</Label>
                  <Input value={code} onChange={(e) => setCode(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Address</Label>
                <Input value={address} onChange={(e) => setAddress(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}>
                {mutation.isPending && <Loader2 className="animate-spin" />}
                <Building2 /> Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (providers?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No providers.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(providers?.results ?? []).map((p) => (
            <Card key={p.id}>
              <CardContent className="pt-6">
                <p className="flex items-center gap-2 font-medium">
                  <Stethoscope className="size-4 text-primary" /> {p.name}
                </p>
                <p className="text-muted-foreground text-xs">
                  {p.code} · {p.phone || "-"}
                </p>
                <p className="text-muted-foreground text-xs">{p.email || "-"}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
