import { useState } from "react";
import { Download, FileBarChart, Loader2, TrendingUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
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
import { downloadBlob, formatCurrency } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

const EXPORTS = [
  { value: "patients", label: "Patients" },
  { value: "invoices", label: "Invoices" },
  { value: "payments", label: "Payments" },
  { value: "medicines", label: "Medicines" },
];

export function ReportsPage() {
  const { error } = useToast();
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (report: string) => {
    setExporting(report);
    try {
      const res = await api.get(`/reports/export/?report=${report}`, { responseType: "blob" });
      const match = /filename="?([^"]+)"?/.exec(res.headers["content-disposition"] ?? "");
      downloadBlob(res.data, match?.[1] ?? `${report}_report.csv`);
    } catch (err) {
      error(getErrorMessage(err, "Unable to export report."));
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Analytics and data exports.">
        <div className="flex flex-wrap gap-2">
          {EXPORTS.map((e) => (
            <Button
              key={e.value}
              variant="outline"
              size="sm"
              onClick={() => handleExport(e.value)}
              disabled={exporting !== null}
            >
              {exporting === e.value ? <Loader2 className="animate-spin" /> : <Download />} {e.label}
            </Button>
          ))}
        </div>
      </PageHeader>

      <Tabs defaultValue="financial">
        <TabsList>
          <TabsTrigger value="financial">Financial</TabsTrigger>
          <TabsTrigger value="patients">Patients</TabsTrigger>
          <TabsTrigger value="medical">Medical</TabsTrigger>
          <TabsTrigger value="inventory">Inventory</TabsTrigger>
        </TabsList>
        <TabsContent value="financial">
          <FinancialReport />
        </TabsContent>
        <TabsContent value="patients">
          <PatientReport />
        </TabsContent>
        <TabsContent value="medical">
          <MedicalReport />
        </TabsContent>
        <TabsContent value="inventory">
          <InventoryReport />
        </TabsContent>
      </Tabs>
    </div>
  );
}

interface FinancialData {
  total_revenue: number;
  outstanding: { total_outstanding: number | null };
  daily_revenue_30d: { date: string; total: number }[];
  payment_methods: { method: string; total: string; count: number }[];
}

function FinancialReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "financial"],
    queryFn: () => api.get<FinancialData>("/reports/financial/").then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-60" />;
  if (!data) return <p className="text-muted-foreground py-10 text-center">No data.</p>;

  const maxDaily = Math.max(...data.daily_revenue_30d.map((d) => d.total), 1);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard icon={TrendingUp} title="Total revenue" value={formatCurrency(data.total_revenue)} />
        <StatCard
          icon={FileBarChart}
          title="Outstanding"
          value={formatCurrency(data.outstanding?.total_outstanding ?? 0)}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Daily revenue (30 days)</CardTitle>
          <CardDescription>Completed payments</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-40 items-end gap-1">
            {data.daily_revenue_30d.map((d) => (
              <div
                key={d.date}
                title={`${d.date}: ${formatCurrency(d.total)}`}
                className="flex-1 rounded-t bg-primary/70 hover:bg-primary"
                style={{ height: `${Math.max((d.total / maxDaily) * 100, 2)}%` }}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Payment methods</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y rounded-lg border">
            {data.payment_methods.map((m) => (
              <div key={m.method} className="flex items-center justify-between p-3 text-sm">
                <span className="capitalize">{m.method}</span>
                <span>
                  {formatCurrency(m.total)} ({m.count})
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface PatientReportData {
  new_patients: number;
  returning_patients: number;
  demographics: { gender: string; count: number }[];
}

function PatientReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "patients"],
    queryFn: () => api.get<PatientReportData>("/reports/patients/").then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-60" />;
  if (!data) return <p className="text-muted-foreground py-10 text-center">No data.</p>;

  const total = data.demographics.reduce((sum, d) => sum + d.count, 0) || 1;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard icon={FileBarChart} title="New patients" value={data.new_patients} />
        <StatCard icon={FileBarChart} title="Returning patients" value={data.returning_patients} />
      </div>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Demographics</CardTitle>
        </CardHeader>
        <CardContent>
          {data.demographics.length === 0 ? (
            <p className="text-muted-foreground text-sm">No demographic data.</p>
          ) : (
            <div className="space-y-3">
              {data.demographics.map((d) => (
                <div key={d.gender}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="capitalize">{d.gender || "unknown"}</span>
                    <span className="text-muted-foreground">
                      {d.count} ({((d.count / total) * 100).toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-2.5 rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${(d.count / total) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface MedicalReportData {
  common_diagnoses: { name: string; count: number }[];
  laboratory_activity: { status: string; count: number }[];
  admissions_by_status: { status: string; count: number }[];
  total_discharges: number;
}

function MedicalReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "medical"],
    queryFn: () => api.get<MedicalReportData>("/reports/medical/").then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-60" />;
  if (!data) return <p className="text-muted-foreground py-10 text-center">No data.</p>;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Common diagnoses</CardTitle>
        </CardHeader>
        <CardContent>
          {data.common_diagnoses.length === 0 ? (
            <p className="text-muted-foreground text-sm">No diagnoses recorded.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {data.common_diagnoses.map((d) => (
                <div key={d.name} className="flex items-center justify-between p-3 text-sm">
                  <span>{d.name}</span>
                  <span className="text-muted-foreground">{d.count}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <div className="space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Laboratory activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y rounded-lg border">
              {data.laboratory_activity.map((l) => (
                <div key={l.status} className="flex items-center justify-between p-3 text-sm">
                  <span className="capitalize">{l.status}</span>
                  <span className="text-muted-foreground">{l.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Admissions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y rounded-lg border">
              {data.admissions_by_status.map((a) => (
                <div key={a.status} className="flex items-center justify-between p-3 text-sm">
                  <span className="capitalize">{a.status}</span>
                  <span className="text-muted-foreground">{a.count}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Total discharges: <span className="font-medium">{data.total_discharges}</span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface InventoryReportData {
  low_stock_count: number;
  low_stock: { name: string; stock: number }[];
  expired: { medicine: string; batch: string; quantity: number; expiry_date: string }[];
}

function InventoryReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "inventory"],
    queryFn: () => api.get<InventoryReportData>("/reports/inventory/").then((r) => r.data),
  });

  if (isLoading) return <Skeleton className="h-60" />;
  if (!data) return <p className="text-muted-foreground py-10 text-center">No data.</p>;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Low stock <span className="text-muted-foreground">({data.low_stock_count})</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data.low_stock.length === 0 ? (
            <p className="text-muted-foreground text-sm">All stock levels are healthy.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {data.low_stock.map((m) => (
                <div key={m.name} className="flex items-center justify-between p-3 text-sm">
                  <span>{m.name}</span>
                  <span className="text-muted-foreground">{m.stock}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Expired batches</CardTitle>
        </CardHeader>
        <CardContent>
          {data.expired.length === 0 ? (
            <p className="text-muted-foreground text-sm">No expired batches.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {data.expired.map((e, i) => (
                <div key={i} className="flex items-center justify-between p-3 text-sm">
                  <span>
                    {e.medicine} ({e.batch})
                  </span>
                  <span className="text-muted-foreground">
                    {e.quantity} · {e.expiry_date}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
