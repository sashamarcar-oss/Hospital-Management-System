import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Eye, Plus, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";
import type { Consultation, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/status-badge";
import { useAuth } from "@/hooks/use-auth";
import { formatDateTime } from "@/lib/utils";

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
};
const STATUS_VARIANTS: Record<string, "info" | "success"> = {
  in_progress: "info",
  completed: "success",
};

export function ConsultationListPage() {
  const { can, user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  if (status) params.status = status;
  if (user?.role_code === "doctor") params.doctor = user.id;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["consultations", params],
    queryFn: () => api.get<Paginated<Consultation>>("/consultations/", { params }).then((r) => r.data),
  });

  const columns: ColumnDef<Consultation>[] = [
    {
      header: "Patient",
      cell: (c) => (
        <div>
          <p className="font-medium">{c.patient_details?.full_name}</p>
          <p className="text-muted-foreground text-xs">{c.patient_details?.patient_number}</p>
        </div>
      ),
    },
    {
      header: "Chief complaint",
      cell: (c) => (
        <span className="text-muted-foreground line-clamp-1 max-w-56">{c.chief_complaint || "—"}</span>
      ),
    },
    {
      header: "Doctor",
      cell: (c) => `Dr. ${c.doctor_details?.first_name ?? ""} ${c.doctor_details?.last_name ?? ""}`,
    },
    {
      header: "Diagnoses",
      cell: (c) => (
        <span className="line-clamp-1 max-w-56">
          {c.diagnoses?.length ? c.diagnoses.map((d) => d.name).join(", ") : "—"}
        </span>
      ),
    },
    {
      header: "Status",
      cell: (c) => <StatusBadge value={c.status} labels={STATUS_LABELS} variants={STATUS_VARIANTS} />,
    },
    {
      header: "Recorded",
      cell: (c) => formatDateTime(c.recorded_at),
    },
    {
      header: "",
      className: "text-right",
      cell: (c) => (
        <Link to={`/consultations/${c.id}`}>
          <Button variant="ghost" size="icon">
            <Eye />
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Consultations" description={`${data?.count?.toLocaleString() ?? 0} consultation records`}>
        {can("consultations.create") && (
          <Link to="/consultations/new">
            <Button>
              <Plus /> New consultation
            </Button>
          </Link>
        )}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load consultations." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        onRowClick={(c) => {
          window.location.href = `/consultations/${c.id}`;
        }}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput value={search} onChange={setSearch} placeholder="Search patient or complaint…" className="sm:max-w-xs" />
            <select
              className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
            {user?.role_code === "doctor" && (
              <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
                <Stethoscope className="size-3.5" /> Showing only your consultations
              </span>
            )}
          </div>
        }
      />
    </div>
  );
}
