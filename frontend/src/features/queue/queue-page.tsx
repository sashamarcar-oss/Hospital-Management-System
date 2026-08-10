import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ListOrdered, PhoneCall, RefreshCw, UserX } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import type { QueueEntry } from "@/lib/types";
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
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  PRIORITY_LABELS,
  PRIORITY_VARIANTS,
  QUEUE_STATUS_LABELS,
  QUEUE_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function QueuePage() {
  const { user, hasRole } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [departmentId, setDepartmentId] = useState<string>("");

  const { data: queues, isLoading, refetch } = useQuery({
    queryKey: ["queue", "active"],
    queryFn: () => api.get<QueueEntry[]>("/appointments/queue/active/").then((r) => r.data),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["queue"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const callMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/queue/${id}/call/`),
    onSuccess: () => {
      success("Patient called");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to call patient.")),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/queue/${id}/complete/`),
    onSuccess: () => {
      success("Queue entry completed");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to complete queue entry.")),
  });

  const skipMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/queue/${id}/skip/`),
    onSuccess: () => {
      success("Patient skipped");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to skip patient.")),
  });

  const active = (queues ?? []).filter((q) => q.status === "waiting" || q.status === "in_consultation");
  const filtered = departmentId ? active.filter((q) => q.department_name === departmentId) : active;
  const waiting = filtered.filter((q) => q.status === "waiting");
  const inConsultation = filtered.filter((q) => q.status === "in_consultation");

  const departments = Array.from(new Set((queues ?? []).map((q) => q.department_name))).sort();
  const canManage = hasRole("receptionist", "admin", "super_admin") || user?.role_code === "doctor";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Queue management"
        description={`${waiting.length} patients waiting · ${inConsultation.length} in consultation`}
      >
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw /> Refresh
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={!departmentId ? "default" : "outline"}
          size="sm"
          onClick={() => setDepartmentId("")}
        >
          All departments
        </Button>
        {departments.map((d) => (
          <Button
            key={d}
            variant={departmentId === d ? "default" : "outline"}
            size="sm"
            onClick={() => setDepartmentId(d)}
          >
            {d}
          </Button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListOrdered className="size-5 text-primary" /> Waiting patients
            </CardTitle>
            <CardDescription>Next up: {waiting[0]?.patient_details?.full_name ?? "—"}</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground py-8 text-center text-sm">Loading queue…</p>
            ) : filtered.length === 0 ? (
              <p className="text-muted-foreground py-12 text-center text-sm">
                No patients in queue for this view.
              </p>
            ) : (
              <div className="space-y-2">
                {filtered.map((q, idx) => (
                  <div
                    key={q.id}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border p-3",
                      q.status === "in_consultation" && "border-primary/40 bg-primary/5",
                      (q.priority === "emergency" || q.priority === "critical") && "border-red-200 bg-red-50 dark:border-red-500/30 dark:bg-red-500/15"
                    )}
                  >
                    <span className="text-muted-foreground w-8 text-center text-lg font-semibold">
                      {idx + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-medium">{q.patient_details?.full_name}</p>
                        <StatusBadge value={q.priority} labels={PRIORITY_LABELS} variants={PRIORITY_VARIANTS} fallback="neutral" />
                        {q.status === "in_consultation" && (
                          <StatusBadge value="in_consultation" labels={QUEUE_STATUS_LABELS} variants={QUEUE_STATUS_VARIANTS} />
                        )}
                      </div>
                      <p className="text-muted-foreground truncate text-xs">
                        {q.patient_details?.patient_number} · {q.department_name}
                        {q.waiting_minutes != null ? ` · waiting ${q.waiting_minutes} min` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {canManage && q.status === "waiting" && (
                        <Button size="sm" onClick={() => callMutation.mutate(q.id)} disabled={inConsultation.length > 0}>
                          <PhoneCall /> Call
                        </Button>
                      )}
                      {canManage && q.status === "in_consultation" && (
                        <Button size="sm" variant="outline" onClick={() => completeMutation.mutate(q.id)}>
                          <CheckCircle2 /> Complete
                        </Button>
                      )}
                      {canManage && q.status === "waiting" && (
                        <Button size="sm" variant="ghost" onClick={() => skipMutation.mutate(q.id)}>
                          <UserX /> Skip
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Now in consultation</CardTitle>
          </CardHeader>
          <CardContent>
            {inConsultation.length === 0 ? (
              <p className="text-muted-foreground text-sm">No patient currently in consultation.</p>
            ) : (
              inConsultation.map((q) => (
                <div key={q.id} className="space-y-1">
                  <p className="text-lg font-semibold">{q.patient_details?.full_name}</p>
                  <p className="text-muted-foreground text-sm">{q.patient_details?.patient_number}</p>
                  <p className="text-muted-foreground text-xs">
                    Called at {q.called_at ? formatTime(q.called_at) : "—"} · {q.department_name}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
