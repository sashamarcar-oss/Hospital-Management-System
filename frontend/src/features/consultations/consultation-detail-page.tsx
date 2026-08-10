import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, FlaskConical, Pill, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";
import type { Consultation, Prescription } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/status-badge";
import { ErrorState } from "@/components/common/states";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatDateTime } from "@/lib/utils";
import { PRESCRIPTION_STATUS_LABELS, PRESCRIPTION_STATUS_VARIANTS } from "@/lib/constants";

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
};
const STATUS_VARIANTS: Record<string, "info" | "success"> = {
  in_progress: "info",
  completed: "success",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm leading-relaxed">
        {children ?? <span className="text-muted-foreground">Not recorded</span>}
      </CardContent>
    </Card>
  );
}

function vitalItems(v: NonNullable<Consultation["vital_signs"]>[number]) {
  return [
    { label: "Temp", value: v.temperature ? `${v.temperature}°C` : null },
    {
      label: "BP",
      value: v.blood_pressure_systolic && v.blood_pressure_diastolic
        ? `${v.blood_pressure_systolic}/${v.blood_pressure_diastolic} mmHg`
        : null,
    },
    { label: "Pulse", value: v.pulse ? `${v.pulse} bpm` : null },
    { label: "Resp", value: v.respiratory_rate ? `${v.respiratory_rate} /min` : null },
    { label: "O₂ sat", value: v.oxygen_saturation ? `${v.oxygen_saturation}%` : null },
    { label: "Weight", value: v.weight ? `${v.weight} kg` : null },
    { label: "Height", value: v.height ? `${v.height} cm` : null },
    { label: "Pain", value: v.pain_score != null ? `${v.pain_score}/10` : null },
  ].filter((i) => i.value);
}

export function ConsultationDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: consultation, isLoading, isError, refetch } = useQuery({
    queryKey: ["consultations", id],
    queryFn: () => api.get<Consultation>(`/consultations/${id}/`).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-72" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    );
  }

  if (isError || !consultation) {
    return (
      <ErrorState
        title="Consultation not found"
        description="This consultation record could not be loaded."
        onRetry={refetch}
      />
    );
  }

  const latestVitals = consultation.vital_signs[consultation.vital_signs.length - 1];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Consultation #{consultation.id}</h1>
          <p className="text-muted-foreground text-sm">
            Recorded {formatDateTime(consultation.recorded_at)} · Dr. {consultation.doctor_details?.first_name}{" "}
            {consultation.doctor_details?.last_name}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge value={consultation.status} labels={STATUS_LABELS} variants={STATUS_VARIANTS} />
          <Button variant="outline" asChild>
            <Link to={`/patients/${consultation.patient}`}>Patient profile</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Section title="Chief complaint">
            <p className="text-base font-medium">{consultation.chief_complaint || "Not recorded"}</p>
          </Section>
          <Section title="History of presenting illness">{consultation.history_of_presenting_illness}</Section>
          <Section title="Symptoms">
            {consultation.symptoms ? (
              <div className="flex flex-wrap gap-2">
                {consultation.symptoms.split(",").map((s, i) => (
                  <Badge key={i} variant="secondary">
                    {s.trim()}
                  </Badge>
                ))}
              </div>
            ) : null}
          </Section>
          <Section title="Physical examination">{consultation.physical_examination}</Section>
          <Section title="Clinical notes">{consultation.clinical_notes}</Section>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Pill className="size-4 text-primary" /> Prescriptions
              </CardTitle>
              <CardDescription>Medication orders associated with this consultation</CardDescription>
            </CardHeader>
            <CardContent>
              {consultation.prescriptions?.length ? (
                <div className="space-y-4">
                  {consultation.prescriptions.map((p: Prescription) => (
                    <div key={p.id} className="rounded-lg border p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold">Prescription #{p.id}</p>
                        <StatusBadge
                          value={p.status}
                          labels={PRESCRIPTION_STATUS_LABELS}
                          variants={PRESCRIPTION_STATUS_VARIANTS}
                        />
                      </div>
                      <div className="divide-y">
                        {p.items.map((item) => (
                          <div key={item.id} className="flex items-center justify-between gap-4 py-2">
                            <div className="min-w-0">
                              <p className="text-sm font-medium">{item.medicine_name}</p>
                              <p className="text-muted-foreground text-xs">
                                {item.dosage} · {item.frequency} · {item.duration} ·{" "}
                                {item.route?.toUpperCase()} · Qty {item.quantity}
                              </p>
                              {item.instructions && (
                                <p className="text-muted-foreground mt-0.5 text-xs">{item.instructions}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No prescriptions recorded.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Stethoscope className="size-4 text-primary" /> Diagnoses
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {consultation.diagnoses?.length ? (
                consultation.diagnoses.map((d) => (
                  <div key={d.id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{d.name}</p>
                      {d.icd_code && <Badge variant="secondary">{d.icd_code}</Badge>}
                    </div>
                    {d.is_primary && <p className="text-muted-foreground mt-1 text-[11px]">Primary</p>}
                    {d.description && <p className="text-muted-foreground mt-1 text-xs">{d.description}</p>}
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground text-sm">No diagnoses recorded.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="size-4 text-primary" /> Vitals at visit
              </CardTitle>
            </CardHeader>
            <CardContent>
              {latestVitals ? (
                <div className="grid grid-cols-2 gap-3">
                  {vitalItems(latestVitals).map((item) => (
                    <div key={item.label} className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-[11px] uppercase">{item.label}</p>
                      <p className="text-sm font-semibold">{item.value}</p>
                    </div>
                  ))}
                  {vitalItems(latestVitals).length === 0 && (
                    <p className="text-muted-foreground col-span-2 text-sm">No vitals recorded.</p>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No vitals recorded.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FlaskConical className="size-4 text-primary" /> Referrals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Treatment plan</p>
                <p>{consultation.treatment_plan || "Not recorded"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Procedures</p>
                <p>{consultation.procedures || "Not recorded"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Follow-up date</p>
                <p>{consultation.follow_up_date ? formatDate(consultation.follow_up_date) : "Not scheduled"}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
