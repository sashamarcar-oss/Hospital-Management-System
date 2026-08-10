import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Download, Eye, Plus, UserRound } from "lucide-react";
import { api } from "@/lib/api";
import type { Paginated, Patient } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { getErrorMessage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { downloadBlob, formatAge, formatDate, initials } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

export function PatientListPage() {
  const { can } = useAuth();
  const { error } = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  Object.entries(filters).forEach(([k, v]) => {
    if (v) params[k] = v;
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["patients", params],
    queryFn: () => api.get<Paginated<Patient>>("/patients/", { params }).then((r) => r.data),
  });

  const handleExport = async () => {
    try {
      const response = await api.get("/patients/export/", {
        params,
        responseType: "blob",
      });
      downloadBlob(response.data, `patients_${new Date().toISOString().slice(0, 10)}.xlsx`);
    } catch (err) {
      error(getErrorMessage(err, "Unable to export patients."));
    }
  };

  const columns: ColumnDef<Patient>[] = [
    {
      header: "Patient",
      cell: (p) => (
        <div className="flex items-center gap-3">
          <Avatar className="size-9">
            {p.profile_photo ? <AvatarImage src={p.profile_photo} alt={p.full_name} /> : null}
            <AvatarFallback className="bg-primary/10 text-primary text-xs">
              {initials(p.first_name, p.last_name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <p className="font-medium">{p.full_name}</p>
            <p className="text-muted-foreground text-xs">{p.patient_number}</p>
          </div>
        </div>
      ),
    },
    {
      header: "Gender",
      cell: (p) => <span className="capitalize">{p.gender}</span>,
    },
    {
      header: "Age",
      cell: (p) => formatAge(p.date_of_birth),
    },
    {
      header: "Phone",
      cell: (p) => p.phone || "—",
    },
    {
      header: "Blood Group",
      cell: (p) => <Badge variant="outline">{p.blood_group}</Badge>,
    },
    {
      header: "Allergies",
      cell: (p) => (
        <span className={p.allergies ? "text-red-600" : "text-muted-foreground"}>
          {p.allergies || "None recorded"}
        </span>
      ),
    },
    {
      header: "Registered",
      cell: (p) => formatDate(p.created_at),
    },
    {
      header: "",
      className: "text-right",
      cell: (p) => (
        <Link to={`/patients/${p.id}`}>
          <Button variant="ghost" size="icon">
            <Eye />
          </Button>
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Patients"
        description={`${data?.count?.toLocaleString() ?? 0} patient records`}
      >
        <Button variant="outline" onClick={handleExport}>
          <Download /> Export
        </Button>
        {can("patients.create") && (
          <Link to="/patients/register">
            <Button>
              <Plus /> Register Patient
            </Button>
          </Link>
        )}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load patients." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        onRowClick={(p) => {
          window.location.href = `/patients/${p.id}`;
        }}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <SearchInput value={search} onChange={setSearch} placeholder="Search name, number, phone, national ID…" className="sm:max-w-xs" />
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
                value={filters.gender ?? ""}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, gender: e.target.value }));
                  setPage(1);
                }}
              >
                <option value="">All genders</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
              <select
                className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
                value={filters.blood_group ?? ""}
                onChange={(e) => {
                  setFilters((f) => ({ ...f, blood_group: e.target.value }));
                  setPage(1);
                }}
              >
                <option value="">All blood groups</option>
                {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                  <option key={bg} value={bg}>{bg}</option>
                ))}
              </select>
              {(search || Object.values(filters).some(Boolean)) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch("");
                    setFilters({});
                    setPage(1);
                  }}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>
        }
      />
    </div>
  );
}
