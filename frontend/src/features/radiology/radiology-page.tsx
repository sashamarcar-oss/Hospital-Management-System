import { useState } from "react";
import { Loader2, Plus, ScanLine } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Paginated, RadiologyRequest } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { StatusBadge } from "@/components/common/status-badge";
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
import { Textarea } from "@/components/ui/textarea";
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
import { PatientSelect } from "@/components/common/patient-select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  PRIORITIES,
  PRIORITY_LABELS,
  RADIOLOGY_PROCEDURE_LABELS,
  RADIOLOGY_STATUS_LABELS,
} from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";

function NewRadiologyRequestDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [patient, setPatient] = useState<number | null>(null);
  const [procedureType, setProcedureType] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [indication, setIndication] = useState("");
  const [priority, setPriority] = useState("routine");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/radiology/", {
        patient,
        doctor: user?.id,
        procedure_type: procedureType,
        body_part: bodyPart,
        clinical_indication: indication,
        priority,
      }),
    onSuccess: () => {
      success("Imaging request created");
      setOpen(false);
      setPatient(null);
      setProcedureType("");
      setBodyPart("");
      setIndication("");
      queryClient.invalidateQueries({ queryKey: ["radiology"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create imaging request.")),
  });

  const submit = () => {
    if (!patient) return error("Select a patient.");
    if (!procedureType) return error("Select a procedure type.");
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New imaging request
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New imaging request</DialogTitle>
          <DialogDescription>Order an X-Ray, ultrasound, CT or MRI.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>
              Patient <span className="text-red-500">*</span>
            </Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>
                Procedure <span className="text-red-500">*</span>
              </Label>
              <Select value={procedureType} onValueChange={setProcedureType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select procedure" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(RADIOLOGY_PROCEDURE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Body part</Label>
              <Input placeholder="e.g. Chest, Left knee" value={bodyPart} onChange={(e) => setBodyPart(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Clinical indication</Label>
            <Input value={indication} onChange={(e) => setIndication(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Priority</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {PRIORITY_LABELS[p]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Create request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ReportDialog({ request }: { request: RadiologyRequest }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [findings, setFindings] = useState("");
  const [impression, setImpression] = useState("");
  const [conclusion, setConclusion] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/radiology/reports/", {
        request: request.id,
        findings,
        impression,
        conclusion,
      }),
    onSuccess: () => {
      success("Report saved");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["radiology"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to save report.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
          <ScanLine /> Add report
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Imaging report — {RADIOLOGY_PROCEDURE_LABELS[request.procedure_type]} ({request.body_part})
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Findings</Label>
            <Textarea rows={4} value={findings} onChange={(e) => setFindings(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Impression</Label>
            <Textarea rows={3} value={impression} onChange={(e) => setImpression(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Conclusion</Label>
            <Textarea rows={2} value={conclusion} onChange={(e) => setConclusion(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Save report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RadiologyPage() {
  const { can } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  if (status) params.status = status;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["radiology", params],
    queryFn: () => api.get<Paginated<RadiologyRequest>>("/radiology/", { params }).then((r) => r.data),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["radiology"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const transition = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => api.post(`/radiology/${id}/${action}/`),
    onSuccess: () => {
      success("Imaging request updated");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update imaging request.")),
  });

  const columns: ColumnDef<RadiologyRequest>[] = [
    {
      header: "Patient",
      cell: (r) => (
        <div>
          <p className="font-medium">{r.patient_details?.full_name}</p>
          <p className="text-muted-foreground text-xs">{r.patient_details?.patient_number}</p>
        </div>
      ),
    },
    {
      header: "Procedure",
      cell: (r) => (
        <div>
          <p className="font-medium">{RADIOLOGY_PROCEDURE_LABELS[r.procedure_type] ?? r.procedure_type}</p>
          {r.body_part && <p className="text-muted-foreground text-xs">{r.body_part}</p>}
        </div>
      ),
    },
    { header: "Indication", cell: (r) => <span className="text-muted-foreground line-clamp-1 max-w-40">{r.clinical_indication || "—"}</span> },
    { header: "Doctor", cell: (r) => `Dr. ${r.doctor_details?.first_name ?? ""} ${r.doctor_details?.last_name ?? ""}` },
    {
      header: "Status",
      cell: (r) => (
        <div>
          <StatusBadge value={r.status} labels={RADIOLOGY_STATUS_LABELS} />
          {r.report && <p className="text-muted-foreground mt-0.5 text-[10px]">Reported</p>}
        </div>
      ),
    },
    { header: "Requested", cell: (r) => formatDateTime(r.requested_at) },
    {
      header: "",
      className: "text-right",
      cell: (r) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              Actions
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Workflow</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {r.status === "requested" && can("radiology.update") && (
              <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "queue" })}>Add to queue</DropdownMenuItem>
            )}
            {r.status === "queued" && can("radiology.update") && (
              <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "start" })}>Start imaging</DropdownMenuItem>
            )}
            {r.status === "in_progress" && can("radiology.update") && (
              <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "complete" })}>Mark completed</DropdownMenuItem>
            )}
            {!r.report && (r.status === "completed" || r.status === "reviewed") && (
              <ReportDialog request={r} />
            )}
            {(r.status === "requested" || r.status === "queued") && (
              <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "cancel" })}>Cancel request</DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Radiology" description={`${data?.count?.toLocaleString() ?? 0} imaging requests`}>
        {can("radiology.create") && <NewRadiologyRequestDialog />}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load imaging requests." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput value={search} onChange={setSearch} placeholder="Search patient…" className="sm:max-w-xs" />
            <select
              className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {Object.entries(RADIOLOGY_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        }
      />
    </div>
  );
}
