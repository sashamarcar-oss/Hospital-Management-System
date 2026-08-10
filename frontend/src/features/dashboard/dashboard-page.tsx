import { Link } from "react-router-dom";
import {
  Users,
  CalendarDays,
  CalendarClock,
  BedDouble,
  BedSingle,
  Stethoscope,
  UserRound,
  FlaskConical,
  Pill,
  Banknote,
  UserPlus,
  ClipboardPlus,
  FilePlus2,
  ReceiptText,
  Microscope,
  Loader2,
  Activity,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { KPIs, DashboardCharts, ActivityItem } from "@/lib/types";
import { useAuth } from "@/hooks/use-auth";
import { StatCard } from "@/components/common/stat-card";
import { ErrorState, EmptyState } from "@/components/common/states";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import {
  AUDIT_ACTION_LABELS,
  APPOINTMENT_STATUS_LABELS,
  APPOINTMENT_STATUS_VARIANTS,
} from "@/lib/constants";
import { StatusBadge } from "@/components/common/status-badge";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PIE_COLORS = ["#0d9488", "#0ea5e9", "#f59e0b", "#ef4444", "#8b5cf6", "#10b981"];

function ChartSkeleton() {
  return <Skeleton className="h-64 w-full" />;
}

export function DashboardPage() {
  const { user, can } = useAuth();

  const { data: kpis, isLoading: kpisLoading, error: kpisError, refetch: refetchKpis } = useQuery({
    queryKey: ["dashboard", "kpis"],
    queryFn: () => api.get<KPIs>("/dashboard/kpis/").then((r) => r.data),
  });

  const { data: charts, isLoading: chartsLoading, error: chartsError, refetch: refetchCharts } = useQuery({
    queryKey: ["dashboard", "charts"],
    queryFn: () => api.get<DashboardCharts>("/dashboard/charts/").then((r) => r.data),
  });

  const { data: activity, isLoading: activityLoading, error: activityError, refetch: refetchActivity } = useQuery({
    queryKey: ["dashboard", "activity"],
    queryFn: () => api.get<ActivityItem[]>("/dashboard/activity/", { params: { limit: 12 } }).then((r) => r.data),
  });

  const quickActions = [
    { label: "Register Patient", to: "/patients/register", icon: UserPlus, show: can("patients.create") },
    { label: "Book Appointment", to: "/appointments/new", icon: CalendarDays, show: can("appointments.create") },
    { label: "New Consultation", to: "/consultations/new", icon: ClipboardPlus, show: can("consultations.create") },
    { label: "Admit Patient", to: "/admissions", icon: BedDouble, show: can("admissions.create") },
    { label: "Create Invoice", to: "/billing", icon: ReceiptText, show: can("billing.create") },
    { label: "Request Lab Test", to: "/laboratory", icon: Microscope, show: can("laboratory.create") },
  ].filter((a) => a.show);

  const revenueSeries = charts?.revenue.map((r) => ({ date: r.date, Revenue: Number(r.value) })) ?? [];
  const registrationsSeries = charts?.patient_registrations.map((r) => ({ date: r.date, Registrations: r.value })) ?? [];

  if (!charts) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back, {user?.first_name || user?.username}
          </h1>
          <p className="text-muted-foreground text-sm">Here is what is happening across the hospital today.</p>
        </div>
        {quickActions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action) => (
              <Link key={action.label} to={action.to}>
                <Button variant="outline" size="sm" className="gap-1.5">
                  <action.icon className="size-4" />
                  {action.label}
                </Button>
              </Link>
            ))}
          </div>
        )}
      </div>

      {kpisLoading ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : kpisError ? (
        <ErrorState description="Unable to load dashboard metrics." onRetry={refetchKpis} />
      ) : kpis ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          <StatCard title="Total Patients" value={kpis.total_patients.toLocaleString()} icon={Users} tone="teal" />
          <StatCard title="Today's Appointments" value={kpis.today_appointments} icon={CalendarDays} tone="blue" />
          <StatCard title="Pending Appointments" value={kpis.pending_appointments} icon={CalendarClock} tone="amber" />
          <StatCard title="Admitted Patients" value={kpis.admitted_patients} icon={BedDouble} tone="violet" />
          <StatCard title="Available Beds" value={kpis.available_beds} icon={BedSingle} tone="emerald" />
          <StatCard title="Doctors" value={kpis.doctors} icon={Stethoscope} tone="blue" />
          <StatCard title="Nurses" value={kpis.nurses} icon={UserRound} tone="slate" />
          <StatCard title="Pending Lab Tests" value={kpis.pending_lab_tests} icon={FlaskConical} tone="amber" />
          <StatCard title="Pending Prescriptions" value={kpis.pending_prescriptions} icon={Pill} tone="violet" />
          <StatCard title="Today's Revenue" value={formatCurrency(kpis.today_revenue)} icon={Banknote} tone="teal" />
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Revenue — last 30 days</CardTitle>
            <CardDescription>Daily revenue trend</CardDescription>
          </CardHeader>
          <CardContent>
            {chartsLoading ? (
              <ChartSkeleton />
            ) : chartsError ? (
              <ErrorState onRetry={refetchCharts} />
            ) : revenueSeries.length === 0 ? (
              <EmptyState title="No revenue data yet" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={revenueSeries} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0d9488" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#0d9488" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                  <Area type="monotone" dataKey="Revenue" stroke="#0d9488" strokeWidth={2} fill="url(#rev)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Appointments by status</CardTitle>
            <CardDescription>Current distribution</CardDescription>
          </CardHeader>
          <CardContent>
            {chartsLoading ? (
              <ChartSkeleton />
            ) : chartsError ? (
              <ErrorState onRetry={refetchCharts} />
            ) : charts.appointments_by_status.length === 0 ? (
              <EmptyState title="No appointments" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={charts.appointments_by_status}
                    dataKey="count"
                    nameKey="status"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {charts.appointments_by_status.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v, name) => [v, APPOINTMENT_STATUS_LABELS[String(name)] ?? String(name)]} />
                  <Legend
                    formatter={(value) => APPOINTMENT_STATUS_LABELS[value] ?? value}
                    iconSize={8}
                    wrapperStyle={{ fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Patient registrations — last 30 days</CardTitle>
            <CardDescription>New patients per day</CardDescription>
          </CardHeader>
          <CardContent>
            {chartsLoading ? (
              <ChartSkeleton />
            ) : chartsError ? (
              <ErrorState onRetry={refetchCharts} />
            ) : registrationsSeries.length === 0 ? (
              <EmptyState title="No registrations yet" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={registrationsSeries} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="Registrations" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="gap-4">
          <CardHeader>
            <CardTitle>Activity feed</CardTitle>
            <CardDescription>Recent system activity</CardDescription>
          </CardHeader>
          <CardContent>
            {activityLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10" />
                ))}
              </div>
            ) : activityError ? (
              <ErrorState onRetry={refetchActivity} />
            ) : activity?.length === 0 ? (
              <EmptyState title="No recent activity" description="Actions performed in the system will appear here." />
            ) : (
              <div className="space-y-1">
                {activity?.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-3 rounded-md p-2 transition-colors hover:bg-muted/50"
                  >
                    <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                      <Activity className="size-3.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm">
                        <span className="font-medium">{item.user || "System"}</span>{" "}
                        <span className="text-muted-foreground">{AUDIT_ACTION_LABELS[item.action] ?? item.action}</span>{" "}
                        <span className="font-medium capitalize">{item.module}</span>
                      </p>
                      {item.description && (
                        <p className="text-muted-foreground line-clamp-1 text-xs">{item.description}</p>
                      )}
                      <p className="text-muted-foreground mt-0.5 text-xs">{formatDateTime(item.timestamp)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Patient demographics</CardTitle>
            <CardDescription>By gender</CardDescription>
          </CardHeader>
          <CardContent>
            {chartsLoading ? (
              <ChartSkeleton />
            ) : chartsError ? (
              <ErrorState onRetry={refetchCharts} />
            ) : charts.patient_demographics.length === 0 ? (
              <EmptyState title="No demographics data" />
            ) : (
              <div className={cn("grid gap-4", "sm:grid-cols-3")}>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={charts.patient_demographics} dataKey="count" nameKey="gender" innerRadius={40} outerRadius={70} paddingAngle={2}>
                      {charts.patient_demographics.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v, name) => [v, String(name)]} />
                    <Legend iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Common diagnoses</CardTitle>
            <CardDescription>Most frequent conditions</CardDescription>
          </CardHeader>
          <CardContent>
            {chartsLoading ? (
              <ChartSkeleton />
            ) : chartsError ? (
              <ErrorState onRetry={refetchCharts} />
            ) : charts.common_diagnoses.length === 0 ? (
              <EmptyState title="No diagnosis data" />
            ) : (
              <div className="space-y-3">
                {charts.common_diagnoses.slice(0, 6).map((d, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-muted-foreground w-5 text-sm font-medium">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <p className="truncate text-sm">{d.name}</p>
                        <span className="text-muted-foreground text-xs">{d.count}</span>
                      </div>
                      <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
                        <div
                          className="bg-primary h-full rounded-full"
                          style={{ width: `${(d.count / charts.common_diagnoses[0].count) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
