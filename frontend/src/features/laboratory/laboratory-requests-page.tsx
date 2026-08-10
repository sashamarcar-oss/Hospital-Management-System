import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Beaker, CheckCheck, FlaskConical, XCircle } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import type { LabRequest, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NewLabRequestDialog } from "@/features/laboratory/new-lab-request-dialog";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  LAB_REQUEST_STATUS_LABELS,
  LAB_REQUEST_STATUS_VARIANTS,
  PRIORITY_LABELS,
  PRIORITY_VARIANTS,
} from "@/lib/constants";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export function LaboratoryRequestsPage() {
  const { can } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  if (status) params.status = status;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["laboratory", "requests", params],
    queryFn: () => api.get<Paginated<LabRequest>>("/laboratory/", { params }).then((r) => r.data),
  });

  const { data: detail } = useQuery({
    queryKey: ["laboratory", "requests", detailId],
    queryFn: () => api.get<LabRequest>(`/laboratory/${detailId}/`).then((r) => r.data),
    enabled: !!detailId,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["laboratory"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const transition = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => api.post(`/laboratory/${id}/${action}/`),
    onSuccess: () => {
      success("Lab request updated");
      invalidate();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update lab request.")),
  });

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
      cell: (r) => (
        <div>
          <p className="font-medium">{r.test_count} tests</p>
          <p className="text-muted-foreground text-xs">{r.items.map((i) => i.test_name).slice(0, 2).join(", ")}{r.items.length > 2 ? "…" : ""}</p>
        </div>
      ),
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
      header: "Doctor",
      cell: (r) => `Dr. ${r.doctor_details?.first_name ?? ""} ${r.doctor_details?.last_name ?? ""}`,
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
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" onClick={() => setDetailId(r.id)}>
            View
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                Actions
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Status workflow</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {r.status === "requested" && can("laboratory.update") && (
                <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "collect_sample" })}>
                  <Beaker /> Collect sample
                </DropdownMenuItem>
              )}
              {r.status === "sample_collected" && can("laboratory.update") && (
                <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "start_processing" })}>
                  <FlaskConical /> Start processing
                </DropdownMenuItem>
              )}
              {r.status === "processing" && can("laboratory.enter_results") && (
                <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "mark_completed" })}>
                  <CheckCheck /> Mark completed
                </DropdownMenuItem>
              )}
              {r.status === "completed" && (
                <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "review" })}>
                  <CheckCheck /> Review
                </DropdownMenuItem>
              )}
              {(r.status === "requested" || r.status === "sample_collected") && (
                <DropdownMenuItem onClick={() => transition.mutate({ id: r.id, action: "cancel" })}>
                  <XCircle /> Cancel request
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Lab requests" description={`${data?.count?.toLocaleString() ?? 0} requests`}>
        {can("laboratory.create") && <NewLabRequestDialog />}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load lab requests." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        onRowClick={(r) => setDetailId(r.id)}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput value={search} onChange={setSearch} placeholder="Search patient…" className="sm:max-w-xs" />
            <select
              className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {Object.entries(LAB_REQUEST_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
        }
      />

      <Dialog open={!!detailId} onOpenChange={(o) => !o && setDetailId(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Lab request #{detail?.id}</DialogTitle>
            <DialogDescription>
              {detail?.patient_details?.full_name} · {detail ? formatDateTime(detail.requested_at) : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <StatusBadge value={detail?.status ?? ""} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
              <span className="text-muted-foreground text-sm">{detail ? formatCurrency(detail.total_price) : ""}</span>
            </div>
            {detail?.clinical_notes && (
              <p className="bg-muted/50 rounded-md p-3 text-sm">{detail.clinical_notes}</p>
            )}
            <div className="divide-y rounded-md border">
              {detail?.items.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <div>
                    <p className="font-medium">{item.test_name}</p>
                    <p className="text-muted-foreground text-xs">
                      Normal: {item.normal_range || "—"} {item.units}
                    </p>
                  </div>
                  {item.result ? (
                    <div className="text-right">
                      <p className="font-semibold">{item.result.result} {item.result.units}</p>
                      <p className="text-muted-foreground text-xs">{item.status}</p>
                    </div>
                  ) : (
                    <span className="text-muted-foreground text-xs">{item.status}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
