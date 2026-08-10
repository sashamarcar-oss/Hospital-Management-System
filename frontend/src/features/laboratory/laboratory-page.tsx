import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Beaker, ClipboardList, FlaskConical, ListChecks } from "lucide-react";
import { api } from "@/lib/api";
import type { LabRequest } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { NewLabRequestDialog } from "@/features/laboratory/new-lab-request-dialog";
import {
  LAB_REQUEST_STATUS_LABELS,
  LAB_REQUEST_STATUS_VARIANTS,
  PRIORITY_LABELS,
  PRIORITY_VARIANTS,
} from "@/lib/constants";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

export function LaboratoryPage() {
  const { can } = useAuth();
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["laboratory", "requests", page],
    queryFn: () =>
      api.get<{ count: number; page: number; total_pages: number; results: LabRequest[] }>("/laboratory/", {
        params: { page },
      }).then((r) => r.data),
  });

  const { data: pending } = useQuery({
    queryKey: ["laboratory", "pending"],
    queryFn: () => api.get<LabRequest[]>("/laboratory/pending/").then((r) => r.data),
  });

  const all = data?.results ?? [];
  const pendingCount = pending?.length ?? 0;
  const processingCount = pending?.filter((r) => r.status === "processing").length ?? 0;

  const columns: ColumnDef<LabRequest>[] = [
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
      header: "Tests",
      cell: (r) => <span className="font-medium">{r.test_count}</span>,
    },
    {
      header: "Priority",
      cell: (r) => <StatusBadge value={r.priority} labels={PRIORITY_LABELS} variants={PRIORITY_VARIANTS} fallback="neutral" />,
    },
    {
      header: "Status",
      cell: (r) => (
        <StatusBadge value={r.status} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
      ),
    },
    {
      header: "Requested",
      cell: (r) => formatDateTime(r.requested_at),
    },
    {
      header: "Total",
      cell: (r) => formatCurrency(r.total_price),
    },
    {
      header: "",
      className: "text-right",
      cell: (r) => (
        <Link to="/laboratory/results">
          <Button variant="ghost" size="sm">
            Details <ArrowRight />
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Laboratory" description="Manage lab requests, samples and results.">
        <Button variant="outline" asChild>
          <Link to="/laboratory/requests">
            <ClipboardList /> All requests
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/laboratory/results">
            <ListChecks /> Results
          </Link>
        </Button>
        {can("laboratory.create") && <NewLabRequestDialog />}
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Beaker} title="Pending requests" value={pendingCount} />
        <StatCard icon={FlaskConical} title="Processing" value={processingCount} />
        <StatCard icon={ClipboardList} title="Total requests" value={data?.count ?? 0} />
      </div>

      <DataTable
        columns={columns}
        data={all}
        loading={isLoading}
        error={isError ? "Unable to load laboratory requests." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        toolbar={<p className="text-muted-foreground text-sm">Recent laboratory activity</p>}
      />
    </div>
  );
}
