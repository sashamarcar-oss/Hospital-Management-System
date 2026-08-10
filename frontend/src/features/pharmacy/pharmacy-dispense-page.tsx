import { useState } from "react";
import { Loader2, Pill, Send } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Paginated, Prescription } from "@/lib/types";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  PRESCRIPTION_STATUS_LABELS,
  PRESCRIPTION_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function PharmacyDispensePage() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [quantities, setQuantities] = useState<Record<number, string>>({});

  const { data: prescriptions, isLoading } = useQuery({
    queryKey: ["pharmacy", "prescriptions", "active"],
    queryFn: () =>
      api
        .get<Paginated<Prescription>>("/consultations/prescriptions/", {
          params: { status: "active", page_size: 50 },
        })
        .then((r) => r.data),
  });

  const selected =
    prescriptions?.results.find((p) => p.id === selectedId) ?? prescriptions?.results[0] ?? null;

  const mutation = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("No prescription selected");
      const items = selected.items
        .filter((item) => Number(quantities[item.id] ?? 0) > 0)
        .map((item) => ({ item: item.id, quantity: Number(quantities[item.id]) }));
      return api.post("/pharmacy/dispense/", { prescription: selected.id, items });
    },
    onSuccess: () => {
      success("Prescription dispensed", "Stock deducted and billing updated.");
      setQuantities({});
      queryClient.invalidateQueries({ queryKey: ["pharmacy"] });
      queryClient.invalidateQueries({ queryKey: ["consultations"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to dispense prescription.")),
  });

  const anyToDispense = selected?.items.some((i) => Number(quantities[i.id] ?? 0) > 0) ?? false;

  return (
    <div className="space-y-6">
      <PageHeader title="Dispense prescriptions" description="Select an active prescription and record quantities dispensed." />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Pill className="size-4 text-primary" /> Active prescriptions
              </CardTitle>
              <CardDescription>Prescriptions waiting for the pharmacy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {isLoading ? (
                <Skeleton className="h-20" />
              ) : (prescriptions?.results ?? []).length === 0 ? (
                <p className="text-muted-foreground text-sm">No active prescriptions.</p>
              ) : (
                (prescriptions?.results ?? []).map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedId(p.id)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted/50",
                      selected?.id === p.id && "border-primary/40 bg-primary/5"
                    )}
                  >
                    <p className="text-sm font-medium">{p.patient_details?.full_name}</p>
                    <p className="text-muted-foreground text-xs">
                      #{p.id} · {p.item_count} items · {formatDateTime(p.created_at)}
                    </p>
                    <StatusBadge value={p.status} labels={PRESCRIPTION_STATUS_LABELS} variants={PRESCRIPTION_STATUS_VARIANTS} />
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Dispense items</CardTitle>
              <CardDescription>
                {selected
                  ? `${selected.patient_details?.full_name} — prescription #${selected.id}`
                  : "No prescription selected"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {selected ? (
                <div className="space-y-4">
                  <div className="divide-y rounded-lg border">
                    {selected.items.map((item) => {
                      const remaining = item.quantity - item.dispensed_quantity;
                      const entered = Number(quantities[item.id] ?? 0);
                      return (
                        <div key={item.id} className="flex items-center justify-between gap-4 p-3">
                          <div className="min-w-0">
                            <p className="text-sm font-medium">{item.medicine_name}</p>
                            <p className="text-muted-foreground text-xs">
                              {item.dosage} · {item.frequency} · {item.duration} · {item.route?.toUpperCase()}
                            </p>
                            <p className="text-muted-foreground text-xs">
                              Qty {item.quantity} · dispensed {item.dispensed_quantity} · remaining {remaining}
                            </p>
                          </div>
                          <div className="w-28 space-y-1">
                            <Label className="text-xs">Qty to dispense</Label>
                            <Input
                              type="number"
                              min={0}
                              max={remaining}
                              value={quantities[item.id] ?? ""}
                              placeholder={`≤ ${remaining}`}
                              onChange={(e) =>
                                setQuantities((prev) => ({ ...prev, [item.id]: e.target.value }))
                              }
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {anyToDispense && (
                    <Button
                      onClick={() => mutation.mutate()}
                      disabled={mutation.isPending}
                      className="w-full"
                    >
                      {mutation.isPending && <Loader2 className="animate-spin" />}
                      <Send /> Dispense selected items
                    </Button>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground py-10 text-center text-sm">
                  Select a prescription to begin dispensing.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
