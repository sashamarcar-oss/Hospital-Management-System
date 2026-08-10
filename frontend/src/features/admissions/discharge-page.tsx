import { useState } from "react";
import { Download, FileText, Loader2, LogOut } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Admission, Discharge, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
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
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { formatDate } from "@/lib/utils";

const DISCHARGE_TYPES = [
  { value: "home", label: "Home" },
  { value: "referral", label: "Referral" },
  { value: "against-medical-advice", label: "Against medical advice" },
];

export function DischargePage() {
  const { data: admissions } = useQuery({
    queryKey: ["admissions", "admitted"],
    queryFn: () =>
      api
        .get<Paginated<Admission>>("/admissions/", { params: { status: "admitted", page_size: 100 } })
        .then((r) => r.data),
  });

  const { data: discharges, isLoading } = useQuery({
    queryKey: ["discharges"],
    queryFn: () =>
      api
        .get<Paginated<Discharge>>("/admissions/discharges/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["discharges"] });

  return (
    <div className="space-y-6">
      <PageHeader title="Discharges" description="Record patient discharges and view discharge summaries.">
        <DischargeDialog
          admissions={(admissions?.results ?? []).filter((a) => a.status === "admitted")}
          onDone={invalidate}
        />
      </PageHeader>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="size-4 text-primary" /> Discharge summaries
          </CardTitle>
          <CardDescription>Completed discharges</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-40" />
          ) : (discharges?.results ?? []).length === 0 ? (
            <p className="text-muted-foreground py-10 text-center text-sm">No discharges recorded.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {(discharges?.results ?? []).map((d) => (
                <div key={d.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="font-medium">{d.patient_details?.full_name}</p>
                    <p className="text-muted-foreground text-xs">
                      {DISCHARGE_TYPES.find((t) => t.value === d.discharge_type)?.label ?? d.discharge_type} ·{" "}
                      discharged {formatDate(d.discharge_date)} · {d.discharged_by_name ?? "-"}
                    </p>
                    {d.diagnosis_summary && (
                      <p className="text-muted-foreground text-xs italic">{d.diagnosis_summary}</p>
                    )}
                  </div>
                  <a href={`${api.defaults.baseURL}/admissions/discharges/${d.id}/pdf/`} target="_blank" rel="noreferrer">
                    <Button variant="outline" size="sm">
                      <Download /> PDF
                    </Button>
                  </a>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DischargeDialog({ admissions, onDone }: { admissions: Admission[]; onDone: () => void }) {
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [admission, setAdmission] = useState<string>("");
  const [dischargeType, setDischargeType] = useState("home");
  const [diagnosisSummary, setDiagnosisSummary] = useState("");
  const [treatmentSummary, setTreatmentSummary] = useState("");
  const [medication, setMedication] = useState("");
  const [outstandingBills, setOutstandingBills] = useState("");
  const [followUpInstructions, setFollowUpInstructions] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");
  const [doctorNotes, setDoctorNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/admissions/discharges/", {
        admission: Number(admission),
        discharge_type: dischargeType,
        diagnosis_summary: diagnosisSummary,
        treatment_summary: treatmentSummary,
        medication,
        outstanding_bills: outstandingBills,
        follow_up_instructions: followUpInstructions,
        follow_up_date: followUpDate || null,
        doctor_notes: doctorNotes,
      }),
    onSuccess: () => {
      success("Patient discharged", "Bed has been freed.");
      setOpen(false);
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to record discharge.")),
  });

  const selected = admissions.find((a) => String(a.id) === admission);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <LogOut /> Discharge patient
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Discharge patient</DialogTitle>
          <DialogDescription>Complete the discharge summary and free the assigned bed.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Admitted patient</Label>
            <Select value={admission} onValueChange={setAdmission}>
              <SelectTrigger><SelectValue placeholder="Select admitted patient" /></SelectTrigger>
              <SelectContent>
                {admissions.map((a) => (
                  <SelectItem key={a.id} value={String(a.id)}>
                    {a.patient_details?.full_name} — {a.ward_name ?? "no ward"} / {a.bed_name ?? "no bed"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selected && (
              <p className="text-muted-foreground text-xs">
                Admitted {formatDate(selected.admission_date)} · {selected.diagnosis || "no diagnosis"}
              </p>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Discharge type</Label>
              <Select value={dischargeType} onValueChange={setDischargeType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {DISCHARGE_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Follow-up date</Label>
              <Input type="date" value={followUpDate} onChange={(e) => setFollowUpDate(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Diagnosis summary</Label>
            <Textarea value={diagnosisSummary} onChange={(e) => setDiagnosisSummary(e.target.value)} rows={2} />
          </div>
          <div className="space-y-2">
            <Label>Treatment summary</Label>
            <Textarea value={treatmentSummary} onChange={(e) => setTreatmentSummary(e.target.value)} rows={2} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Medication on discharge</Label>
              <Textarea value={medication} onChange={(e) => setMedication(e.target.value)} rows={2} />
            </div>
            <div className="space-y-2">
              <Label>Outstanding bills</Label>
              <Textarea value={outstandingBills} onChange={(e) => setOutstandingBills(e.target.value)} rows={2} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Follow-up instructions</Label>
            <Textarea value={followUpInstructions} onChange={(e) => setFollowUpInstructions(e.target.value)} rows={2} />
          </div>
          <div className="space-y-2">
            <Label>Doctor's notes</Label>
            <Textarea value={doctorNotes} onChange={(e) => setDoctorNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!admission || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <LogOut /> Confirm discharge
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
