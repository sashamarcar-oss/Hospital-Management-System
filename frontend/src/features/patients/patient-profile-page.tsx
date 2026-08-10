import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Phone,
  Mail,
  MapPin,
  Droplet,
  AlertTriangle,
  Printer,
  CalendarDays,
  Plus,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  Paginated,
  Patient,
  PatientSummary,
  Consultation,
  Diagnosis,
  VitalSigns,
  Prescription,
  LabRequest,
  RadiologyRequest,
  Admission,
  Invoice,
  InsurancePolicy,
  Document,
  Appointment,
} from "@/lib/types";
import { formatAge, formatCurrency, formatDate, formatDateTime, formatTime } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState, EmptyState } from "@/components/common/states";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { StatusBadge } from "@/components/common/status-badge";
import {
  APPOINTMENT_STATUS_LABELS,
  APPOINTMENT_STATUS_VARIANTS,
  ADMISSION_STATUS_LABELS,
  ADMISSION_STATUS_VARIANTS,
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_VARIANTS,
  LAB_REQUEST_STATUS_LABELS,
  LAB_REQUEST_STATUS_VARIANTS,
  PRESCRIPTION_STATUS_LABELS,
  PRESCRIPTION_STATUS_VARIANTS,
  RADIOLOGY_STATUS_LABELS,
  DOCUMENT_CATEGORY_LABELS,
} from "@/lib/constants";
import { DocumentUploadDialog } from "@/features/documents/document-upload-dialog";

function TabLoading() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-14" />
      ))}
    </div>
  );
}

export function PatientProfilePage() {
  const { id } = useParams<{ id: string }>();
  const { can } = useAuth();
  const patientId = Number(id);

  const { data: patient, isLoading, error } = useQuery({
    queryKey: ["patient", patientId],
    queryFn: () => api.get<Patient>(`/patients/${patientId}/`).then((r) => r.data),
    enabled: !!patientId,
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !patient) {
    return <ErrorState title="Patient not found" description="Unable to load this patient record." />;
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <Avatar className="size-16">
              {patient.profile_photo ? <AvatarImage src={patient.profile_photo} alt={patient.full_name} /> : null}
              <AvatarFallback className="bg-primary/10 text-primary text-xl">
                {patient.first_name.charAt(0)}
                {patient.last_name.charAt(0)}
              </AvatarFallback>
            </Avatar>
            <div>
              <h1 className="text-2xl font-semibold">{patient.full_name}</h1>
              <div className="text-muted-foreground mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                <span>{patient.patient_number}</span>
                <span>{formatAge(patient.date_of_birth)}</span>
                <span className="capitalize">{patient.gender}</span>
                <span>{formatDate(patient.date_of_birth)}</span>
              </div>
              <div className="text-muted-foreground mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                {patient.phone && <span className="flex items-center gap-1"><Phone className="size-3.5" /> {patient.phone}</span>}
                {patient.email && <span className="flex items-center gap-1"><Mail className="size-3.5" /> {patient.email}</span>}
                {patient.address && <span className="flex items-center gap-1"><MapPin className="size-3.5" /> {patient.address}</span>}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {can("patients.print_summary") && (
              <Button variant="outline" onClick={() => window.print()}>
                <Printer /> Print summary
              </Button>
            )}
            {can("appointments.create") && (
              <Link to={`/appointments/new?patient=${patientId}`}>
                <Button><Plus /> Book appointment</Button>
              </Link>
            )}
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <InfoBox label="Blood group" value={patient.blood_group} icon={Droplet} tone="red" />
          <InfoBox label="Allergies" value={patient.allergies || "None"} icon={AlertTriangle} tone="amber" />
          <InfoBox label="Insurance" value={patient.insurance_provider || "—"} />
          <InfoBox label="Next of kin" value={patient.next_of_kin_name || "—"} />
        </div>
      </div>

      <PatientTabs patientId={patientId} patient={patient} />
    </div>
  );
}

function InfoBox({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  tone?: string;
}) {
  return (
    <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-500/15">
      <p className="text-muted-foreground flex items-center gap-1.5 text-xs font-medium">
        {Icon && <Icon className={tone ? `size-3.5 text-${tone}-500` : "size-3.5"} />}
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-medium">{value}</p>
    </div>
  );
}

function PatientTabs({ patientId, patient }: { patientId: number; patient: Patient }) {
  return (
    <Tabs defaultValue="overview">
      <TabsList className="w-full flex-wrap h-auto justify-start gap-1 p-1 sm:w-fit">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="personal">Personal</TabsTrigger>
        <TabsTrigger value="medical">Medical History</TabsTrigger>
        <TabsTrigger value="vitals">Vital Signs</TabsTrigger>
        <TabsTrigger value="consultations">Consultations</TabsTrigger>
        <TabsTrigger value="diagnoses">Diagnoses</TabsTrigger>
        <TabsTrigger value="prescriptions">Prescriptions</TabsTrigger>
        <TabsTrigger value="laboratory">Laboratory</TabsTrigger>
        <TabsTrigger value="imaging">Imaging</TabsTrigger>
        <TabsTrigger value="admissions">Admissions</TabsTrigger>
        <TabsTrigger value="billing">Billing</TabsTrigger>
        <TabsTrigger value="insurance">Insurance</TabsTrigger>
        <TabsTrigger value="documents">Documents</TabsTrigger>
        <TabsTrigger value="appointments">Appointments</TabsTrigger>
      </TabsList>

      <TabsContent value="overview"><OverviewTab patient={patient} patientId={patientId} /></TabsContent>
      <TabsContent value="personal"><PersonalTab patient={patient} /></TabsContent>
      <TabsContent value="medical"><MedicalTab patient={patient} /></TabsContent>
      <TabsContent value="vitals"><VitalsTab patientId={patientId} /></TabsContent>
      <TabsContent value="consultations"><ConsultationsTab patientId={patientId} /></TabsContent>
      <TabsContent value="diagnoses"><DiagnosesTab patientId={patientId} /></TabsContent>
      <TabsContent value="prescriptions"><PrescriptionsTab patientId={patientId} /></TabsContent>
      <TabsContent value="laboratory"><LaboratoryTab patientId={patientId} /></TabsContent>
      <TabsContent value="imaging"><ImagingTab patientId={patientId} /></TabsContent>
      <TabsContent value="admissions"><AdmissionsTab patientId={patientId} /></TabsContent>
      <TabsContent value="billing"><BillingTab patientId={patientId} /></TabsContent>
      <TabsContent value="insurance"><InsuranceTab patientId={patientId} /></TabsContent>
      <TabsContent value="documents"><DocumentsTab patientId={patientId} /></TabsContent>
      <TabsContent value="appointments"><AppointmentsTab patientId={patientId} /></TabsContent>
    </Tabs>
  );
}

function OverviewTab({ patient, patientId }: { patient: Patient; patientId: number }) {
  const { data: consultations } = useQuery({
    queryKey: ["consultations", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Consultation>>(`/consultations/`, { params: { patient: patientId, page_size: 5 } }).then((r) => r.data.results),
  });
  const { data: vitalSigns } = useQuery({
    queryKey: ["vitals", "by-patient", patientId],
    queryFn: () => api.get<VitalSigns[]>(`/consultations/vitals/history/?patient=${patientId}`).then((r) => r.data),
  });
  const { data: labRequests } = useQuery({
    queryKey: ["laboratory", "by-patient", patientId],
    queryFn: () => api.get<Paginated<LabRequest>>(`/laboratory/`, { params: { patient: patientId, page_size: 5 } }).then((r) => r.data.results),
  });

  const latestVitals = vitalSigns?.[vitalSigns.length - 1];

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card>
        <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <DetailRow label="Patient number" value={patient.patient_number} />
          <DetailRow label="Full name" value={patient.full_name} />
          <DetailRow label="Date of birth" value={formatDate(patient.date_of_birth)} />
          <DetailRow label="Age" value={formatAge(patient.date_of_birth)} />
          <DetailRow label="Gender" value={patient.gender} />
          <DetailRow label="Occupation" value={patient.occupation || "—"} />
          <DetailRow label="Registered" value={formatDate(patient.created_at)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Latest vital signs</CardTitle></CardHeader>
        <CardContent>
          {latestVitals ? (
            <div className="grid grid-cols-2 gap-3 text-sm">
              {latestVitals.temperature && <VitalCell label="Temperature" value={`${latestVitals.temperature} °C`} />}
              {latestVitals.blood_pressure_systolic && (
                <VitalCell label="Blood pressure" value={`${latestVitals.blood_pressure_systolic}/${latestVitals.blood_pressure_diastolic}`} />
              )}
              {latestVitals.pulse && <VitalCell label="Pulse" value={`${latestVitals.pulse} bpm`} />}
              {latestVitals.respiratory_rate && <VitalCell label="Resp rate" value={`${latestVitals.respiratory_rate} /min`} />}
              {latestVitals.oxygen_saturation && <VitalCell label="O₂ saturation" value={`${latestVitals.oxygen_saturation}%`} />}
              {latestVitals.weight && <VitalCell label="Weight" value={`${latestVitals.weight} kg`} />}
              {latestVitals.bmi && <VitalCell label="BMI" value={latestVitals.bmi} />}
              {latestVitals.pain_score != null && <VitalCell label="Pain score" value={`${latestVitals.pain_score}/10`} />}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">No vital signs recorded yet.</p>
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader><CardTitle>Recent consultations</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {consultations?.length ? consultations.slice(0, 4).map((c) => (
              <div key={c.id} className="rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{c.chief_complaint || "Consultation"}</p>
                  <StatusBadge value={c.status} labels={{ in_progress: "In Progress", completed: "Completed" }} />
                </div>
                <p className="text-muted-foreground mt-1 text-xs">{formatDateTime(c.recorded_at)}</p>
              </div>
            )) : <p className="text-muted-foreground text-sm">No consultations yet.</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent lab requests</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {labRequests?.length ? labRequests.slice(0, 4).map((r) => (
              <div key={r.id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium">{r.items.map((i) => i.test_name).join(", ") || `Request #${r.id}`}</p>
                  <p className="text-muted-foreground text-xs">{formatDateTime(r.requested_at)}</p>
                </div>
                <StatusBadge value={r.status} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
              </div>
            )) : <p className="text-muted-foreground text-sm">No lab requests yet.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}

function VitalCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 p-2.5 dark:bg-slate-500/15">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="mt-0.5 font-medium">{value}</p>
    </div>
  );
}

function PersonalTab({ patient }: { patient: Patient }) {
  const rows: [string, string][] = [
    ["National ID / Passport", patient.national_id || "—"],
    ["Email", patient.email || "—"],
    ["Phone", patient.phone || "—"],
    ["Address", patient.address || "—"],
    ["Occupation", patient.occupation || "—"],
    ["Marital status", patient.marital_status],
    ["Blood group", patient.blood_group],
    ["Next of kin", patient.next_of_kin_name || "—"],
    ["Next of kin phone", patient.next_of_kin_phone || "—"],
    ["Relationship", patient.next_of_kin_relationship || "—"],
  ];
  return (
    <Card>
      <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map(([label, value]) => <DetailRow key={label} label={label} value={value} />)}
      </CardContent>
    </Card>
  );
}

function MedicalTab({ patient }: { patient: Patient }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Allergies</CardTitle></CardHeader>
        <CardContent>
          {patient.allergies ? (
            <div className="flex flex-wrap gap-2">
              {patient.allergies.split(",").map((a, i) => (
                <Badge key={i} variant="danger">{a.trim()}</Badge>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">No known allergies on record.</p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Insurance</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <DetailRow label="Provider" value={patient.insurance_provider || "—"} />
          <DetailRow label="Insurance number" value={patient.insurance_number || "—"} />
        </CardContent>
      </Card>
    </div>
  );
}

function VitalsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["vitals", "by-patient", patientId],
    queryFn: () => api.get<VitalSigns[]>(`/consultations/vitals/history/?patient=${patientId}`).then((r) => r.data),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No vital signs recorded" description="Vital signs entered by nurses and doctors will appear here." />;
  return (
    <Card>
      <CardContent className="space-y-3">
        {[...data].reverse().map((v) => (
          <div key={v.id} className="flex flex-wrap items-center gap-4 rounded-md border p-3 text-sm">
            <span className="text-muted-foreground w-40">{formatDateTime(v.recorded_at)}</span>
            {v.temperature && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">🌡 {v.temperature}°C</span>}
            {v.blood_pressure_systolic && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">BP {v.blood_pressure_systolic}/{v.blood_pressure_diastolic}</span>}
            {v.pulse && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">Pulse {v.pulse}</span>}
            {v.respiratory_rate && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">RR {v.respiratory_rate}</span>}
            {v.oxygen_saturation && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">O₂ {v.oxygen_saturation}%</span>}
            {v.weight && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">Wt {v.weight}kg</span>}
            {v.bmi && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">BMI {v.bmi}</span>}
            {v.pain_score != null && <span className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-500/15">Pain {v.pain_score}/10</span>}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ConsultationsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["consultations", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Consultation>>(`/consultations/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No consultations" />;
  return (
    <div className="space-y-3">
      {data.map((c) => (
        <Link key={c.id} to={`/consultations/${c.id}`}>
          <Card className="transition-colors hover:bg-muted/40">
            <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{c.chief_complaint || "Consultation"}</p>
                <p className="text-muted-foreground text-sm">Dr. {c.doctor_details?.first_name} {c.doctor_details?.last_name}</p>
              </div>
              <div className="text-muted-foreground flex items-center gap-3 text-sm">
                <span>{formatDateTime(c.recorded_at)}</span>
                <StatusBadge value={c.status} labels={{ in_progress: "In Progress", completed: "Completed" }} />
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

function DiagnosesTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["diagnoses", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Diagnosis>>(`/consultations/diagnoses/`, { params: { patient: patientId, page_size: 100 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No diagnoses recorded" />;
  return (
    <div className="space-y-3">
      {data.map((d) => (
        <div key={d.id} className="flex items-start justify-between rounded-md border p-4">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-medium">{d.name}</p>
              {d.is_primary && <Badge variant="default">Primary</Badge>}
            </div>
            {d.icd_code && <p className="text-muted-foreground text-sm">ICD-10: {d.icd_code}</p>}
            {d.description && <p className="text-muted-foreground mt-1 text-sm">{d.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

function PrescriptionsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["prescriptions", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Prescription>>(`/consultations/prescriptions/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No prescriptions" />;
  return (
    <div className="space-y-3">
      {data.map((p) => (
        <Card key={p.id}>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm">
                <span className="font-medium">Dr. {p.doctor_details?.first_name} {p.doctor_details?.last_name}</span>
                <span className="text-muted-foreground"> · {formatDateTime(p.created_at)}</span>
              </p>
              <StatusBadge value={p.status} labels={PRESCRIPTION_STATUS_LABELS} variants={PRESCRIPTION_STATUS_VARIANTS} />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {p.items.map((item) => (
                <div key={item.id} className="rounded-md bg-slate-50 p-2.5 dark:bg-slate-500/15 text-sm">
                  <p className="font-medium">{item.medicine_name}</p>
                  <p className="text-muted-foreground text-xs">
                    {item.dosage} · {item.frequency} · {item.duration} · {item.route}
                  </p>
                  {item.instructions && <p className="text-muted-foreground mt-1 text-xs">{item.instructions}</p>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function LaboratoryTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["laboratory", "by-patient", patientId],
    queryFn: () => api.get<Paginated<LabRequest>>(`/laboratory/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No laboratory requests" />;
  return (
    <div className="space-y-3">
      {data.map((r) => (
        <Card key={r.id}>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm">
                <span className="font-medium">{r.items.map((i) => i.test_name).join(", ")}</span>
                <span className="text-muted-foreground"> · {formatDateTime(r.requested_at)}</span>
              </p>
              <StatusBadge value={r.status} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
            </div>
            {r.items.filter((i) => i.result).length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2">
                {r.items.filter((i) => i.result).map((i) => (
                  <div key={i.id} className="rounded-md border p-2.5 text-sm">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{i.test_name}</p>
                      {i.result?.is_abnormal && <Badge variant="danger">Abnormal</Badge>}
                    </div>
                    <p className="mt-1">{i.result?.result}</p>
                    <p className="text-muted-foreground text-xs">Reference: {i.result?.reference_range || i.normal_range} {i.units}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ImagingTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["radiology", "by-patient", patientId],
    queryFn: () => api.get<Paginated<RadiologyRequest>>(`/radiology/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No imaging studies" />;
  return (
    <div className="space-y-3">
      {data.map((r) => (
        <Card key={r.id}>
          <CardContent className="flex items-center justify-between">
            <div>
              <p className="font-medium capitalize">{r.procedure_type} — {r.body_part || "N/A"}</p>
              <p className="text-muted-foreground text-sm">{formatDateTime(r.requested_at)}</p>
              {r.report?.impression && <p className="text-muted-foreground mt-1 text-sm">{r.report.impression}</p>}
            </div>
            <StatusBadge value={r.status} labels={RADIOLOGY_STATUS_LABELS} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AdmissionsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admissions", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Admission>>(`/admissions/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No admissions" />;
  return (
    <div className="space-y-3">
      {data.map((a) => (
        <Card key={a.id}>
          <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{a.admission_reason || "Admission"}</p>
              <p className="text-muted-foreground text-sm">
                {a.ward_name} · {a.room_name} · {a.bed_name}
              </p>
            </div>
            <div className="text-muted-foreground flex items-center gap-3 text-sm">
              <span>{formatDateTime(a.admission_date)}</span>
              <StatusBadge value={a.status} labels={ADMISSION_STATUS_LABELS} variants={ADMISSION_STATUS_VARIANTS} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function BillingTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["invoices", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Invoice>>(`/billing/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No invoices" />;
  return (
    <div className="space-y-3">
      {data.map((inv) => (
        <Link key={inv.id} to={`/billing/${inv.id}`}>
          <Card className="transition-colors hover:bg-muted/40">
            <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-medium">{inv.invoice_number}</p>
                <p className="text-muted-foreground text-sm">{formatDate(inv.issued_at)}</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right text-sm">
                  <p className="font-medium">{formatCurrency(inv.total)}</p>
                  <p className="text-muted-foreground">Balance {formatCurrency(inv.balance)}</p>
                </div>
                <StatusBadge value={inv.status} labels={INVOICE_STATUS_LABELS} variants={INVOICE_STATUS_VARIANTS} />
              </div>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}

function InsuranceTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["policies", "by-patient", patientId],
    queryFn: () => api.get<Paginated<InsurancePolicy>>(`/insurance/policies/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No insurance policies" />;
  return (
    <div className="space-y-3">
      {data.map((p) => (
        <Card key={p.id}>
          <CardContent className="flex items-center justify-between">
            <div>
              <p className="font-medium">{p.provider_name}</p>
              <p className="text-muted-foreground text-sm">Policy: {p.policy_number} · {p.membership_number || "No membership number"}</p>
              <p className="text-muted-foreground text-xs">Coverage: {p.coverage_type} · Limit {formatCurrency(p.coverage_limit)}</p>
            </div>
            <div className="text-right text-sm">
              <StatusBadge value={p.status} labels={{ active: "Active", expired: "Expired", suspended: "Suspended", cancelled: "Cancelled" }} />
              <p className="text-muted-foreground mt-1 text-xs">{formatDate(p.start_date)} → {formatDate(p.end_date)}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function DocumentsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch, isError } = useQuery({
    queryKey: ["documents", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Document>>(`/core/documents/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  const { can } = useAuth();
  if (isLoading) return <TabLoading />;
  if (isError) return <ErrorState onRetry={refetch} />;
  return (
    <div className="space-y-4">
      {can("documents.upload") && (
        <div className="flex justify-end">
          <DocumentUploadDialog patientId={patientId} onUploaded={refetch} />
        </div>
      )}
      {!data?.length ? (
        <EmptyState title="No documents" description="Upload medical reports, lab results and other records." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((doc) => (
            <Card key={doc.id}>
              <CardContent className="flex items-center justify-between">
                <div className="min-w-0">
                  <p className="truncate font-medium">{doc.title}</p>
                  <p className="text-muted-foreground text-xs">{DOCUMENT_CATEGORY_LABELS[doc.category] ?? doc.category}</p>
                  <p className="text-muted-foreground text-xs">{(doc.size_bytes / 1024).toFixed(1)} KB · {formatDate(doc.created_at)}</p>
                </div>
                <a href={`/api/core/documents/${doc.id}/download/`} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm">Open</Button>
                </a>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function AppointmentsTab({ patientId }: { patientId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["appointments", "by-patient", patientId],
    queryFn: () => api.get<Paginated<Appointment>>(`/appointments/`, { params: { patient: patientId, page_size: 50 } }).then((r) => r.data.results),
  });
  if (isLoading) return <TabLoading />;
  if (error) return <ErrorState onRetry={refetch} />;
  if (!data?.length) return <EmptyState title="No appointments" />;
  return (
    <div className="space-y-3">
      {data.map((a) => (
        <Card key={a.id}>
          <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">{a.department_name}</p>
              <p className="text-muted-foreground text-sm">
                {formatDate(a.appointment_date)} · {formatTime(a.start_time)}
                {a.doctor_details && ` · Dr. ${a.doctor_details.first_name} ${a.doctor_details.last_name}`}
              </p>
              {a.reason && <p className="text-muted-foreground text-xs">{a.reason}</p>}
            </div>
            <StatusBadge value={a.status} labels={APPOINTMENT_STATUS_LABELS} variants={APPOINTMENT_STATUS_VARIANTS} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
