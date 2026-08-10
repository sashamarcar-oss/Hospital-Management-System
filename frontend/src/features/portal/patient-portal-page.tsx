import { CalendarDays, FileText, Receipt, Stethoscope } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Appointment,
  Document,
  Invoice,
  Paginated,
  Prescription,
} from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  APPOINTMENT_STATUS_LABELS,
  APPOINTMENT_STATUS_VARIANTS,
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_VARIANTS,
  PRESCRIPTION_STATUS_LABELS,
  PRESCRIPTION_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatCurrency, formatDate, formatDateTime, userFullName } from "@/lib/utils";

export function PatientPortalPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Patient portal" description="Your appointments, records, prescriptions and bills." />
      <Tabs defaultValue="appointments">
        <TabsList>
          <TabsTrigger value="appointments">Appointments</TabsTrigger>
          <TabsTrigger value="prescriptions">Prescriptions</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>
        <TabsContent value="appointments">
          <AppointmentsTab />
        </TabsContent>
        <TabsContent value="prescriptions">
          <PrescriptionsTab />
        </TabsContent>
        <TabsContent value="billing">
          <BillingTab />
        </TabsContent>
        <TabsContent value="documents">
          <DocumentsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function AppointmentsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["portal", "appointments"],
    queryFn: () =>
      api
        .get<Paginated<Appointment>>("/appointments/", { params: { page_size: 50, ordering: "-appointment_date" } })
        .then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-40" />;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarDays className="size-4 text-primary" /> Upcoming and past appointments
        </CardTitle>
      </CardHeader>
      <CardContent>
        {(data?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-6 text-center text-sm">No appointments.</p>
        ) : (
          <div className="divide-y rounded-lg border">
            {(data?.results ?? []).map((a) => (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium">
                    {userFullName(a.doctor_details) || "Doctor"} ·{" "}
                    {a.department_name || "Department"}
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {formatDate(a.appointment_date)} at {a.start_time} · {a.reason || "-"}
                  </p>
                </div>
                <StatusBadge value={a.status} labels={APPOINTMENT_STATUS_LABELS} variants={APPOINTMENT_STATUS_VARIANTS} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PrescriptionsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["portal", "prescriptions"],
    queryFn: () =>
      api
        .get<Paginated<Prescription>>("/consultations/prescriptions/", { params: { page_size: 50 } })
        .then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-40" />;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Stethoscope className="size-4 text-primary" /> My prescriptions
        </CardTitle>
      </CardHeader>
      <CardContent>
        {(data?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-6 text-center text-sm">No prescriptions.</p>
        ) : (
          <div className="divide-y rounded-lg border">
            {(data?.results ?? []).map((p) => (
              <div key={p.id} className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">Prescription #{p.id}</p>
                  <StatusBadge value={p.status} labels={PRESCRIPTION_STATUS_LABELS} variants={PRESCRIPTION_STATUS_VARIANTS} />
                </div>
                <p className="text-muted-foreground text-xs">{formatDateTime(p.created_at)}</p>
                <div className="mt-2 space-y-1">
                  {p.items.map((item) => (
                    <p key={item.id} className="text-sm">
                      {item.medicine_name} — {item.dosage} {item.frequency} {item.duration}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BillingTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["portal", "billing"],
    queryFn: () =>
      api.get<Paginated<Invoice>>("/billing/", { params: { page_size: 50, ordering: "-issued_at" } }).then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-40" />;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Receipt className="size-4 text-primary" /> My invoices
        </CardTitle>
      </CardHeader>
      <CardContent>
        {(data?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-6 text-center text-sm">No invoices.</p>
        ) : (
          <div className="divide-y rounded-lg border">
            {(data?.results ?? []).map((inv) => (
              <div key={inv.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium">{inv.invoice_number}</p>
                  <p className="text-muted-foreground text-xs">{formatDate(inv.issued_at)}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatCurrency(inv.total)}</p>
                  <p className="text-muted-foreground text-xs">
                    balance {formatCurrency(inv.balance)}
                  </p>
                </div>
                <StatusBadge value={inv.status} labels={INVOICE_STATUS_LABELS} variants={INVOICE_STATUS_VARIANTS} />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DocumentsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["portal", "documents"],
    queryFn: () =>
      api.get<Paginated<Document>>("/core/documents/", { params: { page_size: 50 } }).then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-40" />;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="size-4 text-primary" /> My documents
        </CardTitle>
        <CardDescription>Medical records shared with you</CardDescription>
      </CardHeader>
      <CardContent>
        {(data?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-6 text-center text-sm">No documents.</p>
        ) : (
          <div className="divide-y rounded-lg border">
            {(data?.results ?? []).map((d) => (
              <div key={d.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium">{d.title}</p>
                  <p className="text-muted-foreground text-xs">
                    {d.category} · {formatDateTime(d.created_at)}
                  </p>
                </div>
                {d.file && (
                  <a href={`${api.defaults.baseURL}/core/documents/${d.id}/download/`} target="_blank" rel="noreferrer">
                    <span className="text-primary text-sm underline">Download</span>
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
