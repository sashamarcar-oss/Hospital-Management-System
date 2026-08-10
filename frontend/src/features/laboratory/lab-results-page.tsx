import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, Loader2, TestTubes } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import type { LabRequest, LabResult, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/common/states";
import { useToast } from "@/hooks/use-toast";
import {
  LAB_REQUEST_STATUS_LABELS,
  LAB_REQUEST_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

function ResultEntry({ request }: { request: LabRequest }) {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<string, { result: string; units: string; comments: string }>>({});
  const [saving, setSaving] = useState<number | null>(null);

  const pendingItems = request.items.filter((i) => !i.result);

  const mutation = useMutation({
    mutationFn: ({ itemId, payload }: { itemId: number; payload: Record<string, string> }) =>
      api.post("/laboratory/results/", payload).then(() => itemId),
    onSuccess: (itemId) => {
      success("Result saved");
      queryClient.invalidateQueries({ queryKey: ["laboratory"] });
      setValues((prev) => {
        const next = { ...prev };
        delete next[itemId];
        return next;
      });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to save result.")),
  });

  const save = async (itemId: number) => {
    const entry = values[itemId] ?? { result: "", units: "", comments: "" };
    if (!entry.result) {
      error("Enter a result value first.");
      return;
    }
    setSaving(itemId);
    await mutation.mutateAsync({
      itemId,
      payload: {
        request_item: String(itemId),
        result: entry.result,
        units: entry.units,
        comments: entry.comments,
      },
    });
    setSaving(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold">
            {request.patient_details?.full_name} — #{request.id}
          </p>
          <p className="text-muted-foreground text-xs">{request.patient_details?.patient_number}</p>
        </div>
        <StatusBadge value={request.status} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
      </div>
      {pendingItems.length === 0 ? (
        <p className="text-muted-foreground text-sm">All results have been entered for this request.</p>
      ) : (
        pendingItems.map((item) => (
          <div key={item.id} className="rounded-lg border p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium">{item.test_name}</p>
              <p className="text-muted-foreground text-xs">
                Normal: {item.normal_range || "—"} {item.units}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-[1fr_120px]">
              <div className="space-y-1.5">
                <Label className="text-xs">Result</Label>
                <Input
                  placeholder="e.g. 12.5"
                  value={values[item.id]?.result ?? ""}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [item.id]: { ...(prev[item.id] ?? { units: "", comments: "" }), result: e.target.value } }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Units</Label>
                <Input
                  placeholder={item.units || "units"}
                  value={values[item.id]?.units ?? item.units}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [item.id]: { ...(prev[item.id] ?? { result: "", comments: "" }), units: e.target.value } }))
                  }
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label className="text-xs">Comments</Label>
                <Textarea
                  rows={1}
                  placeholder="Interpretation notes…"
                  value={values[item.id]?.comments ?? ""}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [item.id]: { ...(prev[item.id] ?? { result: "", units: "" }), comments: e.target.value } }))
                  }
                />
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <Button size="sm" onClick={() => save(item.id)} disabled={saving === item.id}>
                {saving === item.id && <Loader2 className="animate-spin" />}
                <CheckCheck /> Save result
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export function LabResultsPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const { data: requests, isLoading: loadingRequests } = useQuery({
    queryKey: ["laboratory", "pending"],
    queryFn: () => api.get<LabRequest[]>("/laboratory/pending/").then((r) => r.data),
  });

  const { data: selected } = useQuery({
    queryKey: ["laboratory", "requests", selectedId],
    queryFn: () => api.get<LabRequest>(`/laboratory/${selectedId}/`).then((r) => r.data),
    enabled: !!selectedId,
  });

  const { data: results, isLoading, isError, refetch } = useQuery({
    queryKey: ["laboratory", "results", page],
    queryFn: () => api.get<Paginated<LabResult>>("/laboratory/results/", { params: { page } }).then((r) => r.data),
  });

  const activeRequest = selected ?? requests?.find((r) => r.id === selectedId) ?? requests?.[0];

  return (
    <div className="space-y-6">
      <PageHeader title="Lab results" description="Enter results and review completed tests." />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <TestTubes className="size-4 text-primary" /> Awaiting results
              </CardTitle>
              <CardDescription>Requests needing result entry</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {loadingRequests ? (
                <Skeleton className="h-20" />
              ) : (requests ?? []).length === 0 ? (
                <p className="text-muted-foreground text-sm">No pending requests.</p>
              ) : (
                (requests ?? []).map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted/50",
                      activeRequest?.id === r.id && "border-primary/40 bg-primary/5"
                    )}
                  >
                    <p className="text-sm font-medium">{r.patient_details?.full_name}</p>
                    <p className="text-muted-foreground text-xs">
                      {r.patient_details?.patient_number} · {r.test_count} tests
                    </p>
                    <StatusBadge value={r.status} labels={LAB_REQUEST_STATUS_LABELS} variants={LAB_REQUEST_STATUS_VARIANTS} />
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Enter results</CardTitle>
            </CardHeader>
            <CardContent>
              {activeRequest ? (
                <ResultEntry key={activeRequest.id} request={activeRequest} />
              ) : (
                <p className="text-muted-foreground py-8 text-center text-sm">
                  Select a request to enter its results.
                </p>
              )}
            </CardContent>
          </Card>

          <div className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Completed results</CardTitle>
              </CardHeader>
              <CardContent>
                {isError ? (
                  <ErrorState title="Unable to load results" onRetry={refetch} />
                ) : (
                  <div className="space-y-2">
                    {(results?.results ?? []).map((r) => (
                      <div key={r.id} className="flex items-center justify-between gap-3 rounded-lg border p-3 text-sm">
                        <div>
                          <p className="font-medium">{r.test_name}</p>
                          <p className="text-muted-foreground text-xs">
                            {formatDateTime(r.completed_at)} · {r.technician_name}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className={cn("font-semibold", r.is_abnormal && "text-destructive")}>
                            {r.result} {r.units}
                          </p>
                          <p className="text-muted-foreground text-xs">Ref: {r.reference_range || "—"}</p>
                        </div>
                      </div>
                    ))}
                    {results && results.results.length === 0 && (
                      <p className="text-muted-foreground py-6 text-center text-sm">No results entered yet.</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
