import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  CheckCircle2,
  CircleSlash,
  ClipboardCheck,
  LogIn,
  Plus,
  XCircle,
} from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import type { Appointment, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { StatusBadge } from "@/components/common/status-badge";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  APPOINTMENT_STATUS_LABELS,
  APPOINTMENT_STATUS_VARIANTS,
  PRIORITY_LABELS,
  PRIORITY_VARIANTS,
} from "@/lib/constants";
import { formatDate, formatTime } from "@/lib/utils";

export function AppointmentListPage() {
  const { can } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [date, setDate] = useState("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  if (status) params.status = status;
  if (date) params.appointment_date = date;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["appointments", params],
    queryFn: () => api.get<Paginated<Appointment>>("/appointments/", { params }).then((r) => r.data),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["appointments"] });
    queryClient.invalidateQueries({ queryKey: ["queue"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const confirmMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/${id}/confirm/`),
    onSuccess: () => {
      success("Appointment confirmed");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to confirm appointment.")),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/${id}/cancel/`),
    onSuccess: () => {
      success("Appointment cancelled");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to cancel appointment.")),
  });

  const checkInMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/${id}/checkin/`),
    onSuccess: () => {
      success("Patient checked in");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to check in patient.")),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/${id}/complete/`),
    onSuccess: () => {
      success("Appointment completed");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to complete appointment.")),
  });

  const noShowMutation = useMutation({
    mutationFn: (id: number) => api.post(`/appointments/${id}/noshow/`),
    onSuccess: () => {
      success("Appointment marked no-show");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update appointment.")),
  });

  const columns: ColumnDef<Appointment>[] = [
    {
      header: "Patient",
      cell: (a) => (
        <div>
          <p className="font-medium">{a.patient_details?.full_name}</p>
          <p className="text-muted-foreground text-xs">{a.patient_details?.patient_number}</p>
        </div>
      ),
    },
    {
      header: "Date & Time",
      cell: (a) => (
        <div>
          <p>{formatDate(a.appointment_date)}</p>
          <p className="text-muted-foreground text-xs">
            {formatTime(a.start_time)} – {formatTime(a.end_time)}
          </p>
        </div>
      ),
    },
    {
      header: "Department",
      cell: (a) => a.department_name || "—",
    },
    {
      header: "Doctor",
      cell: (a) =>
        a.doctor_details ? `Dr. ${a.doctor_details.first_name} ${a.doctor_details.last_name}` : "—",
    },
    {
      header: "Reason",
      cell: (a) => <span className="text-muted-foreground line-clamp-1 max-w-48">{a.reason || "—"}</span>,
    },
    {
      header: "Priority",
      cell: (a) => <StatusBadge value={a.priority} labels={PRIORITY_LABELS} variants={PRIORITY_VARIANTS} fallback="neutral" />,
    },
    {
      header: "Status",
      cell: (a) => (
        <StatusBadge value={a.status} labels={APPOINTMENT_STATUS_LABELS} variants={APPOINTMENT_STATUS_VARIANTS} />
      ),
    },
    {
      header: "",
      className: "text-right",
      cell: (a) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              Actions
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Appointment #{a.id}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <Link to={`/patients/${a.patient}`}>
              <DropdownMenuItem>View patient</DropdownMenuItem>
            </Link>
            {a.status === "scheduled" && can("appointments.update") && (
              <DropdownMenuItem onClick={() => confirmMutation.mutate(a.id)}>
                <CheckCircle2 /> Confirm
              </DropdownMenuItem>
            )}
            {(a.status === "scheduled" || a.status === "confirmed") && can("appointments.check_in") && (
              <DropdownMenuItem onClick={() => checkInMutation.mutate(a.id)}>
                <LogIn /> Check in
              </DropdownMenuItem>
            )}
            {a.status === "checked_in" && can("appointments.complete") && (
              <DropdownMenuItem onClick={() => completeMutation.mutate(a.id)}>
                <ClipboardCheck /> Mark completed
              </DropdownMenuItem>
            )}
            {(a.status === "scheduled" || a.status === "confirmed") && can("appointments.cancel") && (
              <ConfirmDialog
                title="Cancel appointment?"
                description={`Cancel the appointment for ${a.patient_details?.full_name} on ${formatDate(a.appointment_date)}?`}
                confirmLabel="Cancel appointment"
                onConfirm={() => cancelMutation.mutate(a.id)}
              >
                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                  <XCircle /> Cancel appointment
                </DropdownMenuItem>
              </ConfirmDialog>
            )}
            {(a.status === "scheduled" || a.status === "confirmed") && (
              <DropdownMenuItem onClick={() => noShowMutation.mutate(a.id)}>
                <CircleSlash /> Mark no-show
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Appointments" description={`${data?.count?.toLocaleString() ?? 0} appointments`}>
        <Link to="/appointments/calendar">
          <Button variant="outline">
            <CalendarDays /> Calendar
          </Button>
        </Link>
        {can("appointments.create") && (
          <Button onClick={() => navigate("/appointments/new")}>
            <Plus /> Book appointment
          </Button>
        )}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load appointments." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        toolbar={
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <SearchInput value={search} onChange={setSearch} placeholder="Search patient or reason…" className="md:max-w-xs" />
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All statuses</option>
                {Object.entries(APPOINTMENT_STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
              <Input
                type="date"
                className="h-9 w-auto"
                value={date}
                onChange={(e) => {
                  setDate(e.target.value);
                  setPage(1);
                }}
              />
              {(search || status || date) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch("");
                    setStatus("");
                    setDate("");
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
