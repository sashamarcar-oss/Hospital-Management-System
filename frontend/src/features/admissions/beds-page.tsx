import { useState } from "react";
import { BedDouble, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Bed } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { BED_STATUS_LABELS, BED_STATUS_VARIANTS, WARD_TYPE_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface WardBoard {
  ward: { id: number; name: string; type: string };
  beds: Bed[];
}

const BED_DOT: Record<string, string> = {
  available: "bg-emerald-500",
  occupied: "bg-rose-500",
  reserved: "bg-amber-500",
  maintenance: "bg-slate-400",
};

export function BedsPage() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Bed | null>(null);
  const [newStatus, setNewStatus] = useState<string>("available");

  const { data: board, isLoading } = useQuery({
    queryKey: ["beds", "board"],
    queryFn: () =>
      api.get<WardBoard[]>("/admissions/beds/board/").then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/admissions/beds/${selected!.id}/set_status/`, { status: newStatus }),
    onSuccess: () => {
      success("Bed updated");
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["beds"] });
      queryClient.invalidateQueries({ queryKey: ["admissions"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update bed.")),
  });

  const counts = (board ?? []).reduce(
    (acc, w) => {
      w.beds.forEach((b) => {
        acc[b.status] = (acc[b.status] ?? 0) + 1;
      });
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Bed management" description="Live bed board grouped by ward.">
        <div className="flex flex-wrap gap-3">
          {Object.entries(BED_STATUS_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={cn("size-2.5 rounded-full", BED_DOT[key])} />
              {label} {counts[key] ?? 0}
            </div>
          ))}
        </div>
      </PageHeader>

      {isLoading ? (
        <Skeleton className="h-60" />
      ) : (board ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No wards configured.</p>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {(board ?? []).map((ward) => (
            <Card key={ward.ward.id}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <BedDouble className="size-4 text-primary" />
                  {ward.ward.name}
                </CardTitle>
                <CardDescription>
                  {WARD_TYPE_LABELS[ward.ward.type] ?? ward.ward.type} ·{" "}
                  {ward.beds.filter((b) => b.status === "available").length} of {ward.beds.length}{" "}
                  available
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-2">
                  {ward.beds.map((bed) => (
                    <button
                      key={bed.id}
                      onClick={() => { setSelected(bed); setNewStatus(bed.status); }}
                      title={`${bed.bed_number} — ${BED_STATUS_LABELS[bed.status]}`}
                      className={cn(
                        "flex aspect-square flex-col items-center justify-center rounded-lg border text-xs font-medium transition-colors hover:opacity-80",
                        BED_STATUS_VARIANTS[bed.status] === "success" && "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
                        BED_STATUS_VARIANTS[bed.status] === "destructive" && "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300",
                        BED_STATUS_VARIANTS[bed.status] === "warning" && "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
                        BED_STATUS_VARIANTS[bed.status] === "neutral" && "border-slate-300 bg-slate-50 text-slate-500 dark:border-slate-500/30 dark:bg-slate-500/15 dark:text-slate-300"
                      )}
                    >
                      <span>{bed.bed_number}</span>
                      {bed.current_patient && (
                        <span className="max-w-full truncate px-1 text-[10px] font-normal">
                          {bed.current_patient.full_name}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              Bed {selected?.bed_number} — {selected?.room_name}
            </DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(BED_STATUS_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setNewStatus(key)}
                className={cn(
                  "rounded-lg border p-3 text-sm font-medium transition-colors",
                  newStatus === key
                    ? "border-primary bg-primary/5 text-primary"
                    : "hover:bg-muted/50"
                )}
              >
                <span className={cn("mb-1.5 block size-2.5 rounded-full", BED_DOT[key])} />
                {label}
              </button>
            ))}
          </div>
          <DialogFooter>
            <Button
              onClick={() => mutation.mutate()}
              disabled={!selected || newStatus === selected.status || mutation.isPending}
            >
              {mutation.isPending && <Loader2 className="animate-spin" />}
              Save status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
