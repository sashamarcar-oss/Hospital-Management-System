import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { Document, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DocumentUploadDialog } from "@/features/documents/document-upload-dialog";
import { DOCUMENT_CATEGORY_LABELS } from "@/lib/constants";
import { formatDateTime, formatFileSize } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

export function DocumentsPage() {
  const { can } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;
  if (category) params.category = category;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", params],
    queryFn: () => api.get<Paginated<Document>>("/core/documents/", { params }).then((r) => r.data),
  });

  const columns: ColumnDef<Document>[] = [
    {
      header: "Title",
      cell: (d) => (
        <div className="flex items-center gap-2">
          <FileText className="text-muted-foreground size-4 shrink-0" />
          <div className="min-w-0">
            <p className="truncate font-medium">{d.title}</p>
            {d.description && (
              <p className="text-muted-foreground line-clamp-1 text-xs">{d.description}</p>
            )}
          </div>
        </div>
      ),
    },
    {
      header: "Patient",
      cell: (d) => d.patient_name || "—",
    },
    {
      header: "Category",
      cell: (d) => <Badge variant="secondary">{DOCUMENT_CATEGORY_LABELS[d.category] ?? d.category}</Badge>,
    },
    {
      header: "Size",
      cell: (d) => formatFileSize(d.size_bytes),
    },
    {
      header: "Uploaded by",
      cell: (d) => (
        <div>
          <p>{d.uploaded_by_name || "—"}</p>
          <p className="text-muted-foreground text-xs">{formatDateTime(d.created_at)}</p>
        </div>
      ),
    },
    {
      header: "",
      className: "text-right",
      cell: (d) => (
        <Button size="icon" variant="ghost" asChild title="Download">
          <a href={d.file_url} target="_blank" rel="noreferrer">
            <FileDown />
          </a>
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Documents" description={`${data?.count?.toLocaleString() ?? 0} documents on record`}>
        {can("documents.upload") && <DocumentUploadDialog />}
      </PageHeader>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        loading={isLoading}
        error={isError ? "Unable to load documents." : null}
        onRetry={refetch}
        count={data?.count}
        page={data?.page ?? page}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        toolbar={
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <SearchInput value={search} onChange={setSearch} placeholder="Search documents…" className="sm:max-w-xs" />
            <select
              className="border-input h-9 rounded-md border bg-transparent px-3 text-sm"
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All categories</option>
              {Object.entries(DOCUMENT_CATEGORY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
        }
      />
    </div>
  );
}
