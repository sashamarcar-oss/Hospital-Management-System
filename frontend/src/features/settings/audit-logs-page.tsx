import { useState } from "react";
import { History, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditLog, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime } from "@/lib/utils";

const ACTION_LABELS: Record<string, string> = {
  create: "Create",
  update: "Update",
  delete: "Delete",
  payment: "Payment",
  upload: "Upload",
  download: "Download",
};

export function AuditLogsPage() {
  const [module, setModule] = useState("all");
  const [action, setAction] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data: logs, isLoading } = useQuery({
    queryKey: ["audit-logs", module, action, search, page],
    queryFn: () =>
      api
        .get<Paginated<AuditLog>>("/core/audit-logs/", {
          params: {
            module: module === "all" ? undefined : module,
            action: action === "all" ? undefined : action,
            search: search || undefined,
            page,
            page_size: 25,
          },
        })
        .then((r) => r.data),
  });

  const modules = Array.from(
    new Set((logs?.results ?? []).map((l) => l.module))
  ).sort();

  return (
    <div className="space-y-6">
      <PageHeader title="Audit logs" description="A complete trail of system activity." />

      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="Search record, description or user..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="max-w-xs"
        />
        <Select value={module} onValueChange={(v) => { setModule(v); setPage(1); }}>
          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All modules</SelectItem>
            {modules.map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={action} onValueChange={(v) => { setAction(v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {Object.entries(ACTION_LABELS).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (logs?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No log entries found.</p>
      ) : (
        <>
          <div className="divide-y rounded-lg border">
            {(logs?.results ?? []).map((log) => (
              <div key={log.id} className="flex flex-wrap items-start justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="font-medium">
                    {ACTION_LABELS[log.action] ?? log.action} · {log.record}
                  </p>
                  <p className="text-muted-foreground text-sm">{log.description || "-"}</p>
                  <p className="text-muted-foreground text-xs">
                    {log.module} · by {log.user_name ?? "system"} · IP {log.ip_address ?? "-"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="flex items-center gap-1 text-muted-foreground text-xs">
                    <History className="size-3" /> {formatDateTime(log.created_at)}
                  </p>
                  {log.new_value !== null && log.new_value !== undefined && (
                    <details className="mt-1 text-xs">
                      <summary className="cursor-pointer text-muted-foreground">Payload</summary>
                      <pre className="mt-1 max-w-md overflow-auto rounded bg-muted p-2">
                        {typeof log.new_value === "string"
                          ? log.new_value
                          : JSON.stringify(log.new_value, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>

          {logs && logs.count > 25 && (
            <div className="flex items-center justify-between text-sm">
              <p className="text-muted-foreground">
                Page {page} of {Math.ceil(logs.count / 25)}
              </p>
              <div className="flex gap-2">
                <button
                  className="rounded border px-3 py-1 disabled:opacity-50"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </button>
                <button
                  className="rounded border px-3 py-1 disabled:opacity-50"
                  disabled={page >= Math.ceil(logs.count / 25)}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
