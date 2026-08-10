import { useState } from "react";
import { Ambulance, Loader2, Plus, Stethoscope, UserCheck, XCircle } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { EmergencyVisit, Paginated, Staff } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { PatientSelect } from "@/components/common/patient-select";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  ARRIVAL_MODE_LABELS,
  EMERGENCY_PRIORITY_LABELS,
  EMERGENCY_PRIORITY_VARIANTS,
  EMERGENCY_STATUS_LABELS,
} from "@/lib/constants";
import { cn, formatDateTime, userFullName } from "@/lib/utils";
export function EmergencyPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("active");

  const { data: visits, isLoading } = useQuery({
    queryKey: ["emergency", filter],
    queryFn: () =>
      filter === "active"
        ? api.get<EmergencyVisit[]>("/emergency/active/").then((r) => r.data)
        : api
            .get<Paginated<EmergencyVisit>>("/emergency/", {
              params: { page_size: 100, ordering: "-arrival_time" },
            })
            .then((r) => r.data.results),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["emergency"] });

  return (
    <div className="space-y-6">
      <PageHeader title="Emergency department" description="Triage and treat emergency cases.">
        <TriageDialog onDone={invalidate} />
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        <Button
          variant={filter === "active" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("active")}
        >
          Active
        </Button>
        <Button
          variant={filter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          All visits
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (visits ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No emergency visits.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(visits ?? []).map((v) => (
            <VisitRow key={v.id} visit={v} onDone={invalidate} />
          ))}
        </div>
      )}
    </div>
  );
}

function VisitRow({ visit, onDone }: { visit: EmergencyVisit; onDone: () => void }) {
  const { success, error } = useToast();
  const [assignOpen, setAssignOpen] = useState(false);
  const [doctor, setDoctor] = useState("");
  const [dischargeNotes, setDischargeNotes] = useState("");

  const { data: staff } = useQuery({
    queryKey: ["staff", "options"],
    queryFn: () =>
      api.get<Paginated<Staff>>("/staff/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: ({ action, payload }: { action: string; payload?: Record<string, unknown> }) =>
      api.post(`/emergency/${visit.id}/${action}/`, payload ?? {}),
    onSuccess: () => {
      success("Visit updated");
      setAssignOpen(false);
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Action failed.")),
  });

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="font-medium">
          {visit.patient_details?.full_name}{" "}
          <span className="text-muted-foreground text-xs">#{visit.patient_details?.patient_number}</span>
        </p>
        <p className="text-muted-foreground text-xs">
          {EMERGENCY_STATUS_LABELS[visit.status]} ·{" "}
          {ARRIVAL_MODE_LABELS[visit.mode_of_arrival] ?? visit.mode_of_arrival} · arrived{" "}
          {formatDateTime(visit.arrival_time)}
          {visit.waiting_minutes != null ? ` · waiting ${visit.waiting_minutes}m` : ""}
        </p>
        <p className="text-muted-foreground text-xs italic">{visit.chief_complaint || "-"}</p>
        {visit.assigned_doctor_details && (
          <p className="text-muted-foreground text-xs">
            Doctor: {userFullName(visit.assigned_doctor_details)}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-medium",
            EMERGENCY_PRIORITY_VARIANTS[visit.priority] === "danger" && "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
            EMERGENCY_PRIORITY_VARIANTS[visit.priority] === "warning" && "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
            EMERGENCY_PRIORITY_VARIANTS[visit.priority] === "neutral" && "bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300",
            EMERGENCY_PRIORITY_VARIANTS[visit.priority] === "info" && "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300"
          )}
        >
          {EMERGENCY_PRIORITY_LABELS[visit.priority] ?? visit.priority}
        </span>

        <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              <UserCheck /> Assign doctor
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>Assign doctor</DialogTitle>
            </DialogHeader>
            <div className="space-y-2">
              <Label>Doctor</Label>
              <Select value={doctor} onValueChange={setDoctor}>
                <SelectTrigger><SelectValue placeholder="Select doctor" /></SelectTrigger>
                <SelectContent>
                  {(staff?.results ?? []).map((s) => (
                    <SelectItem key={s.id} value={String(s.user)}>
                      {userFullName(s.user_details)} ({s.job_title || "staff"})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button
                onClick={() => mutation.mutate({ action: "assign_doctor", payload: { doctor: Number(doctor) } })}
                disabled={!doctor || mutation.isPending}
              >
                {mutation.isPending && <Loader2 className="animate-spin" />}
                Assign
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {(visit.status === "triage" || visit.status === "waiting") && (
          <Button variant="outline" size="sm" onClick={() => mutation.mutate({ action: "start_treatment" })}>
            <Stethoscope /> Start treatment
          </Button>
        )}
        {(visit.status === "triage" || visit.status === "waiting" || visit.status === "in_treatment") && (
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Ambulance /> Discharge
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-sm">
              <DialogHeader>
                <DialogTitle>Complete emergency visit</DialogTitle>
                <DialogDescription>Discharge the patient or add referral notes.</DialogDescription>
              </DialogHeader>
              <div className="space-y-2">
                <Label>Treatment notes / referral notes</Label>
                <Textarea
                  value={dischargeNotes}
                  onChange={(e) => setDischargeNotes(e.target.value)}
                  rows={4}
                />
              </div>
              <DialogFooter className="flex-col gap-2">
                <Button
                  onClick={() => mutation.mutate({ action: "discharge", payload: { treatment_notes: dischargeNotes } })}
                  disabled={mutation.isPending}
                >
                  Discharge
                </Button>
                <Button
                  variant="outline"
                  onClick={() => mutation.mutate({ action: "refer", payload: { notes: dischargeNotes } })}
                  disabled={mutation.isPending}
                >
                  Refer
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => mutation.mutate({ action: "admit" })}
                  disabled={mutation.isPending}
                >
                  Admit to ward
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
}

function TriageDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [patient, setPatient] = useState<number | null>(null);
  const [modeOfArrival, setModeOfArrival] = useState("walk_in");
  const [priority, setPriority] = useState("medium");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [triageNotes, setTriageNotes] = useState("");
  const [triageScore, setTriageScore] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/emergency/", {
        patient,
        mode_of_arrival: modeOfArrival,
        priority,
        chief_complaint: chiefComplaint,
        triage_notes: triageNotes,
        triage_score: triageScore ? Number(triageScore) : null,
      }),
    onSuccess: () => {
      success("Visit triaged", "Patient added to the emergency queue.");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to triage patient.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Triage patient
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Triage emergency patient</DialogTitle>
          <DialogDescription>Register arrival and record initial triage information.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Patient</Label>
            <PatientSelect value={patient} onChange={setPatient} />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label>Arrival mode</Label>
              <Select value={modeOfArrival} onValueChange={setModeOfArrival}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(ARRIVAL_MODE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Triage score</Label>
              <Input
                type="number"
                min={0}
                max={10}
                value={triageScore}
                onChange={(e) => setTriageScore(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Chief complaint</Label>
            <Textarea value={chiefComplaint} onChange={(e) => setChiefComplaint(e.target.value)} rows={2} />
          </div>
          <div className="space-y-2">
            <Label>Triage notes</Label>
            <Textarea value={triageNotes} onChange={(e) => setTriageNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!patient || !chiefComplaint.trim() || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <XCircle /> Complete triage
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
