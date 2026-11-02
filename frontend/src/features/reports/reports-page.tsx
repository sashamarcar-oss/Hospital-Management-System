import { useState, type ReactNode } from "react";
import {
  Activity,
  AlertCircle,
  Bed,
  Boxes,
  CalendarDays,
  CheckCircle2,
  CreditCard,
  Download,
  FileBarChart,
  HeartPulse,
  Loader2,
  Package,
  Pill,
  RefreshCw,
  Stethoscope,
  TrendingUp,
  Users,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, getErrorMessage } from "@/lib/api";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { downloadBlob, formatCurrency, formatDate, titleCase } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

type ReportModule = "Patients" | "Financial" | "Medical" | "Inventory";
type ViewMode = "reports" | "analytics";

interface DateCount {
  date: string;
  count: number;
}

interface PatientReportData {
  new_patients: number;
  returning_patients: number;
  registrations_30d: DateCount[];
  demographics: { gender: string; count: number }[];
  visits_30d: DateCount[];
}

interface FinancialReportData {
  total_revenue: number;
  outstanding: { total_outstanding: number | string | null };
  daily_revenue_30d: { date: string; total: number | string }[];
  monthly_revenue: { month: string; total: number | string }[];
  payment_methods: { method: string; total: number | string; count: number }[];
  insurance_claims: { status: string; total: number | string; count: number }[];
}

interface MedicalReportData {
  common_diagnoses: { name: string; count: number }[];
  laboratory_activity: { status: string; count: number }[];
  admissions_by_status: { status: string; count: number }[];
  total_discharges: number;
  treatments: { icd_code: string; name: string; count: number }[];
}

interface InventoryReportData {
  current_stock: { name: string; stock: number; reorder_level: number }[];
  low_stock_count: number;
  low_stock: { name: string; stock: number }[];
  expired: { medicine: string; batch: string; quantity: number; expiry_date: string }[];
  recent_movements: { medicine: string; type: string; quantity: number; date: string }[];
}

const MODULES: { name: ReportModule; icon: typeof Users; description: string }[] = [
  { name: "Patients", icon: Users, description: "Patient registrations, demographics, and visits" },
  { name: "Financial", icon: CreditCard, description: "Revenue, receivables, payment methods, and claims" },
  { name: "Medical", icon: HeartPulse, description: "Diagnoses, laboratory activity, and admissions" },
  { name: "Inventory", icon: Boxes, description: "Medicine stock, expiries, and stock movements" },
];

const CHART_COLORS = ["#0f766e", "#2563eb", "#d97706", "#7c3aed", "#dc2626", "#0891b2"];

function asNumber(value: number | string | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{children}</p>;
}

function ReportTable({
  headers,
  rows,
  empty = "No data available.",
}: {
  headers: string[];
  rows: ReactNode[][];
  empty?: string;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {headers.map((header) => (
              <th key={header} className="whitespace-nowrap px-4 py-3 text-left font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((row, index) => (
            <tr key={index} className="border-b last:border-0">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-4 py-3">{cell}</td>
              ))}
            </tr>
          )) : (
            <tr><td colSpan={headers.length}><EmptyState>{empty}</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ChartCard({ title, description, children }: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ReportError({ error, retry }: { error: unknown; retry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
        <AlertCircle className="size-8 text-destructive" />
        <p className="max-w-lg text-sm text-muted-foreground">
          {getErrorMessage(error, "Unable to load this report. Please try again.")}
        </p>
        <Button variant="outline" size="sm" onClick={retry}>
          <RefreshCw /> Retry
        </Button>
      </CardContent>
    </Card>
  );
}

function LoadingReport() {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-28" />)}
      </div>
      <Skeleton className="h-72" />
    </div>
  );
}

function PatientReport({ data, mode }: { data: PatientReportData; mode: ViewMode }) {
  const registrations = data.registrations_30d.map((item) => ({
    ...item,
    label: formatDate(item.date),
  }));
  const visits = data.visits_30d.map((item) => ({
    ...item,
    label: formatDate(item.date),
  }));
  const totalDemographics = data.demographics.reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Users} title="New patients" value={data.new_patients} tone="blue" hint="Total patient registrations" />
        <StatCard icon={CheckCircle2} title="Returning patients" value={data.returning_patients} tone="teal" hint="Patients with more than one appointment" />
        <StatCard icon={CalendarDays} title="Registrations (30 days)" value={data.registrations_30d.reduce((sum, item) => sum + item.count, 0)} tone="violet" />
        <StatCard icon={Activity} title="Visits (30 days)" value={data.visits_30d.reduce((sum, item) => sum + item.count, 0)} tone="amber" />
      </div>

      {mode === "analytics" ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Patient registrations" description="Daily registrations over the past 30 days">
            {registrations.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={registrations}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" name="Registrations" stroke="#0f766e" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <EmptyState>No registration activity in the past 30 days.</EmptyState>}
          </ChartCard>
          <ChartCard title="Visits" description="Daily appointments over the past 30 days">
            {visits.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={visits}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Visits" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState>No visits in the past 30 days.</EmptyState>}
          </ChartCard>
          <ChartCard title="Patient demographics">
            {data.demographics.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={data.demographics} dataKey="count" nameKey="gender" outerRadius={90} label>
                    {data.demographics.map((item, index) => (
                      <Cell key={item.gender || `gender-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <EmptyState>No demographic data recorded.</EmptyState>}
          </ChartCard>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Patient demographics" description={`${totalDemographics} patients represented`}>
            {data.demographics.length ? (
              <ReportTable
                headers={["GENDER", "PATIENTS", "SHARE"]}
                rows={data.demographics.map((item) => [
                  titleCase(item.gender || "unknown"),
                  item.count,
                  `${totalDemographics ? Math.round((item.count / totalDemographics) * 100) : 0}%`,
                ])}
              />
            ) : <EmptyState>No demographic data recorded.</EmptyState>}
          </ChartCard>
          <ChartCard title="Reporting coverage" description="Recent patient and appointment activity">
            <ReportTable
              headers={["MEASURE", "COUNT"]}
              rows={[
                ["New registrations (30 days)", data.registrations_30d.reduce((sum, item) => sum + item.count, 0)],
                ["Appointments (30 days)", data.visits_30d.reduce((sum, item) => sum + item.count, 0)],
                ["Returning patients", data.returning_patients],
              ]}
            />
          </ChartCard>
        </div>
      )}
    </div>
  );
}

function FinancialReport({ data, mode }: { data: FinancialReportData; mode: ViewMode }) {
  const methods = data.payment_methods.map((item) => ({ ...item, amount: asNumber(item.total) }));
  const claims = data.insurance_claims.map((item) => ({ ...item, amount: asNumber(item.total) }));
  const monthlyRevenue = data.monthly_revenue.map((item) => ({
    ...item,
    amount: asNumber(item.total),
    label: formatDate(item.month),
  }));
  const dailyRevenue = data.daily_revenue_30d.map((item) => ({
    ...item,
    amount: asNumber(item.total),
    label: formatDate(item.date),
  }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={TrendingUp} title="Collected revenue" value={formatCurrency(data.total_revenue)} tone="teal" hint="Completed payments" />
        <StatCard icon={FileBarChart} title="Outstanding balance" value={formatCurrency(data.outstanding?.total_outstanding)} tone="amber" hint="Unpaid and partially paid invoices" />
        <StatCard icon={CreditCard} title="Payment methods" value={data.payment_methods.length} tone="blue" hint="Methods with completed payments" />
        <StatCard icon={FileBarChart} title="Insurance claim statuses" value={data.insurance_claims.length} tone="violet" />
      </div>

      {mode === "analytics" ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Daily collected revenue" description="Completed payments over the past 30 days">
            {dailyRevenue.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dailyRevenue}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(typeof value === "number" || typeof value === "string" ? value : 0)} />
                  <Bar dataKey="amount" name="Revenue" fill="#0f766e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState>No completed payments in the past 30 days.</EmptyState>}
          </ChartCard>
          <ChartCard title="Monthly revenue" description="Completed payments by month">
            {monthlyRevenue.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={monthlyRevenue}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(typeof value === "number" || typeof value === "string" ? value : 0)} />
                  <Line type="monotone" dataKey="amount" name="Revenue" stroke="#2563eb" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <EmptyState>No monthly revenue data.</EmptyState>}
          </ChartCard>
          <ChartCard title="Payment methods">
            <ReportTable
              headers={["METHOD", "PAYMENTS", "COLLECTED"]}
              rows={methods.map((item) => [titleCase(item.method), item.count, formatCurrency(item.amount)])}
            />
          </ChartCard>
          <ChartCard title="Insurance claims" description="Approved amounts grouped by claim status">
            <ReportTable
              headers={["STATUS", "CLAIMS", "APPROVED AMOUNT"]}
              rows={claims.map((item) => [titleCase(item.status), item.count, formatCurrency(item.amount)])}
            />
          </ChartCard>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Payment methods" description="Completed payment totals by method">
            <ReportTable
              headers={["METHOD", "PAYMENTS", "COLLECTED"]}
              rows={methods.map((item) => [titleCase(item.method), item.count, formatCurrency(item.amount)])}
            />
          </ChartCard>
          <ChartCard title="Insurance claims" description="Claim counts and approved amounts by status">
            <ReportTable
              headers={["STATUS", "CLAIMS", "APPROVED AMOUNT"]}
              rows={claims.map((item) => [titleCase(item.status), item.count, formatCurrency(item.amount)])}
            />
          </ChartCard>
        </div>
      )}
    </div>
  );
}

function MedicalReport({ data, mode }: { data: MedicalReportData; mode: ViewMode }) {
  const admissions = data.admissions_by_status.map((item) => ({ ...item, label: titleCase(item.status) }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Stethoscope} title="Diagnoses (top 20)" value={data.common_diagnoses.reduce((sum, item) => sum + item.count, 0)} tone="blue" />
        <StatCard icon={Activity} title="Lab request statuses" value={data.laboratory_activity.length} tone="violet" />
        <StatCard icon={Bed} title="Admissions" value={data.admissions_by_status.reduce((sum, item) => sum + item.count, 0)} tone="amber" />
        <StatCard icon={CheckCircle2} title="Total discharges" value={data.total_discharges} tone="teal" />
      </div>

      {mode === "analytics" ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Most common diagnoses" description="Top diagnoses recorded in consultations">
            {data.common_diagnoses.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data.common_diagnoses.slice(0, 10)} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="count" name="Cases" fill="#0f766e" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState>No diagnoses recorded.</EmptyState>}
          </ChartCard>
          <ChartCard title="Admissions by status">
            {admissions.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={admissions} dataKey="count" nameKey="label" outerRadius={90} label>
                    {admissions.map((item, index) => (
                      <Cell key={item.status} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <EmptyState>No admission data.</EmptyState>}
          </ChartCard>
          <ChartCard title="Laboratory activity">
            <ReportTable
              headers={["STATUS", "REQUESTS"]}
              rows={data.laboratory_activity.map((item) => [titleCase(item.status), item.count])}
            />
          </ChartCard>
          <ChartCard title="Diagnoses and treatments">
            <ReportTable
              headers={["ICD CODE", "DIAGNOSIS", "CASES"]}
              rows={data.treatments.slice(0, 10).map((item) => [item.icd_code || "—", item.name, item.count])}
            />
          </ChartCard>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Common diagnoses" description="Most frequently recorded diagnoses">
            <ReportTable
              headers={["DIAGNOSIS", "CASES"]}
              rows={data.common_diagnoses.map((item) => [item.name, item.count])}
            />
          </ChartCard>
          <div className="space-y-5">
            <ChartCard title="Laboratory activity">
              <ReportTable
                headers={["STATUS", "REQUESTS"]}
                rows={data.laboratory_activity.map((item) => [titleCase(item.status), item.count])}
              />
            </ChartCard>
            <ChartCard title="Admissions by status">
              <ReportTable
                headers={["STATUS", "ADMISSIONS"]}
                rows={admissions.map((item) => [item.label, item.count])}
              />
            </ChartCard>
          </div>
        </div>
      )}
    </div>
  );
}

function InventoryReport({ data, mode }: { data: InventoryReportData; mode: ViewMode }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={Pill} title="Medicines tracked" value={data.current_stock.length} tone="blue" />
        <StatCard icon={AlertCircle} title="Low-stock medicines" value={data.low_stock_count} tone="amber" hint="At or below reorder level" />
        <StatCard icon={Package} title="Expired batches" value={data.expired.length} tone="red" />
        <StatCard icon={Activity} title="Recent movements" value={data.recent_movements.length} tone="teal" hint="Most recent stock activity" />
      </div>

      {mode === "analytics" ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Current medicine stock" description="Stock on hand compared with reorder levels">
            {data.current_stock.length ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={data.current_stock.slice(0, 12)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="stock" name="Current stock" fill="#0f766e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="reorder_level" name="Reorder level" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState>No medicine stock data.</EmptyState>}
          </ChartCard>
          <ChartCard title="Low-stock items">
            <ReportTable
              headers={["MEDICINE", "CURRENT STOCK"]}
              rows={data.low_stock.map((item) => [item.name, item.stock])}
              empty="All medicine stock levels are healthy."
            />
          </ChartCard>
          <ChartCard title="Expired batches">
            <ReportTable
              headers={["MEDICINE", "BATCH", "QUANTITY", "EXPIRY DATE"]}
              rows={data.expired.map((item) => [item.medicine, item.batch, item.quantity, formatDate(item.expiry_date)])}
              empty="No expired medicine batches."
            />
          </ChartCard>
          <ChartCard title="Recent stock movements">
            <ReportTable
              headers={["MEDICINE", "MOVEMENT", "QUANTITY", "DATE"]}
              rows={data.recent_movements.slice(0, 12).map((item) => [
                item.medicine,
                titleCase(item.type),
                item.quantity,
                formatDate(item.date),
              ])}
            />
          </ChartCard>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <ChartCard title="Low-stock items" description="Medicines at or below reorder level">
            <ReportTable
              headers={["MEDICINE", "CURRENT STOCK"]}
              rows={data.low_stock.map((item) => [item.name, item.stock])}
              empty="All medicine stock levels are healthy."
            />
          </ChartCard>
          <ChartCard title="Expired batches">
            <ReportTable
              headers={["MEDICINE", "BATCH", "QUANTITY", "EXPIRY DATE"]}
              rows={data.expired.map((item) => [item.medicine, item.batch, item.quantity, formatDate(item.expiry_date)])}
              empty="No expired medicine batches."
            />
          </ChartCard>
          <ChartCard title="Current stock">
            <ReportTable
              headers={["MEDICINE", "STOCK", "REORDER LEVEL"]}
              rows={data.current_stock.map((item) => [item.name, item.stock, item.reorder_level])}
            />
          </ChartCard>
          <ChartCard title="Recent stock movements">
            <ReportTable
              headers={["MEDICINE", "MOVEMENT", "QUANTITY", "DATE"]}
              rows={data.recent_movements.slice(0, 12).map((item) => [
                item.medicine,
                titleCase(item.type),
                item.quantity,
                formatDate(item.date),
              ])}
            />
          </ChartCard>
        </div>
      )}
    </div>
  );
}

export function ReportsPage() {
  const { error } = useToast();
  const queryClient = useQueryClient();
  const [view, setView] = useState<ViewMode>("reports");
  const [module, setModule] = useState<ReportModule>("Patients");
  const [exporting, setExporting] = useState<string | null>(null);

  const patients = useQuery({
    queryKey: ["reports", "patients"],
    queryFn: () => api.get<PatientReportData>("/reports/patients/").then((response) => response.data),
  });
  const financial = useQuery({
    queryKey: ["reports", "financial"],
    queryFn: () => api.get<FinancialReportData>("/reports/financial/").then((response) => response.data),
  });
  const medical = useQuery({
    queryKey: ["reports", "medical"],
    queryFn: () => api.get<MedicalReportData>("/reports/medical/").then((response) => response.data),
  });
  const inventory = useQuery({
    queryKey: ["reports", "inventory"],
    queryFn: () => api.get<InventoryReportData>("/reports/inventory/").then((response) => response.data),
  });

  const handleExport = async (report: string) => {
    setExporting(report);
    try {
      const response = await api.get(`/reports/export/?report=${report}`, { responseType: "blob" });
      const match = /filename="?([^"]+)"?/.exec(response.headers["content-disposition"] ?? "");
      downloadBlob(response.data, match?.[1] ?? `${report}_report.csv`);
    } catch (exportError) {
      error(getErrorMessage(exportError, "Unable to export report."));
    } finally {
      setExporting(null);
    }
  };

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["reports"] });
  const activeQuery = {
    Patients: patients,
    Financial: financial,
    Medical: medical,
    Inventory: inventory,
  }[module];

  const renderActiveReport = () => {
    if (activeQuery.isLoading) return <LoadingReport />;
    if (activeQuery.isError) return <ReportError error={activeQuery.error} retry={() => void activeQuery.refetch()} />;
    switch (module) {
      case "Patients":
        return patients.data ? <PatientReport data={patients.data} mode={view} /> : null;
      case "Financial":
        return financial.data ? <FinancialReport data={financial.data} mode={view} /> : null;
      case "Medical":
        return medical.data ? <MedicalReport data={medical.data} mode={view} /> : null;
      case "Inventory":
        return inventory.data ? <InventoryReport data={inventory.data} mode={view} /> : null;
    }
  };

  const exports = module === "Patients"
    ? [{ value: "patients", label: "Patients" }]
    : module === "Financial"
      ? [{ value: "invoices", label: "Invoices" }, { value: "payments", label: "Payments" }]
      : module === "Inventory"
        ? [{ value: "medicines", label: "Medicines" }]
        : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports & Analytics"
        description="Hospital performance, patient activity, clinical outcomes, and operational insights."
      >
        <div className="flex flex-wrap gap-2">
          {exports.map((item) => (
            <Button
              key={item.value}
              variant="outline"
              size="sm"
              onClick={() => void handleExport(item.value)}
              disabled={exporting !== null}
            >
              {exporting === item.value ? <Loader2 className="animate-spin" /> : <Download />}
              Export {item.label}
            </Button>
          ))}
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw /> Refresh
          </Button>
        </div>
      </PageHeader>

      <Tabs value={view} onValueChange={(value) => setView(value as ViewMode)}>
        <TabsList>
          <TabsTrigger value="reports"><FileBarChart /> Reports</TabsTrigger>
          <TabsTrigger value="analytics"><TrendingUp /> Analytics</TabsTrigger>
        </TabsList>

        <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
          {MODULES.map(({ name, icon: Icon, description }) => (
            <Button
              key={name}
              variant={module === name ? "default" : "outline"}
              className="shrink-0"
              onClick={() => setModule(name)}
              title={description}
            >
              <Icon /> {name}
            </Button>
          ))}
        </div>

        <TabsContent value="reports" className="mt-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold">{module} report</h2>
            <p className="text-sm text-muted-foreground">
              {MODULES.find((item) => item.name === module)?.description}
            </p>
          </div>
          {renderActiveReport()}
        </TabsContent>

        <TabsContent value="analytics" className="mt-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold">{module} analytics</h2>
            <p className="text-sm text-muted-foreground">
              Visual summaries and trends based on available hospital data.
            </p>
          </div>
          {renderActiveReport()}
        </TabsContent>
      </Tabs>
    </div>
  );
}
