import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Activity, Loader2, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Paginated, VitalSigns } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { DataTable, type ColumnDef } from "@/components/common/data-table";
import { SearchInput } from "@/components/common/search-input";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PatientSelect } from "@/components/common/patient-select";
import { useToast } from "@/hooks/use-toast";
import { handleMutationError } from "@/lib/mutation-error";
import { formatDateTime } from "@/lib/utils";

const vitalsSchema = z.object({
  patient: z.number({ message: "Select a patient" }),
  temperature: z.string().optional(),
  blood_pressure_systolic: z.coerce.number().optional(),
  blood_pressure_diastolic: z.coerce.number().optional(),
  pulse: z.coerce.number().optional(),
  respiratory_rate: z.coerce.number().optional(),
  oxygen_saturation: z.coerce.number().optional(),
  weight: z.string().optional(),
  height: z.string().optional(),
  pain_score: z.coerce.number().min(0).max(10).optional(),
  notes: z.string().optional(),
});

type VitalsForm = z.infer<typeof vitalsSchema>;

function RecordVitalsDialog() {
  const { success } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const form = useForm<VitalsForm>({
    resolver: zodResolver(vitalsSchema),
    defaultValues: {
      patient: undefined as unknown as number,
      temperature: "",
      blood_pressure_systolic: undefined,
      blood_pressure_diastolic: undefined,
      pulse: undefined,
      respiratory_rate: undefined,
      oxygen_saturation: undefined,
      weight: "",
      height: "",
      pain_score: undefined,
      notes: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: VitalsForm) =>
      api.post("/consultations/vitals/", {
        ...values,
        temperature: values.temperature || null,
        weight: values.weight || null,
        height: values.height || null,
      }),
    onSuccess: () => {
      success("Vital signs recorded");
      setOpen(false);
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["vitals"] });
    },
    onError: (err) =>
      handleMutationError(err, "Unable to record vital signs.", (fieldErrors) => {
        Object.entries(fieldErrors).forEach(([k, v]) => {
          const field = k as keyof VitalsForm;
          if (field in form.getValues()) form.setError(field, { message: v });
        });
      }),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Record vitals
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Record vital signs</DialogTitle>
          <DialogDescription>Enter the patient's current vital signs.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>
              Patient <span className="text-red-500">*</span>
            </Label>
            <PatientSelect
              value={form.watch("patient") ?? null}
              onChange={(id) => form.setValue("patient", id ?? (undefined as unknown as number))}
            />
            {form.formState.errors.patient && (
              <p className="text-destructive text-sm">{form.formState.errors.patient.message}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {(
              [
                ["temperature", "Temp (°C)", "37.0"],
                ["blood_pressure_systolic", "BP sys", "120"],
                ["blood_pressure_diastolic", "BP dia", "80"],
                ["pulse", "Pulse", "72"],
                ["respiratory_rate", "Resp rate", "16"],
                ["oxygen_saturation", "O₂ (%)", "98"],
                ["weight", "Weight (kg)", "70"],
                ["height", "Height (cm)", "170"],
                ["pain_score", "Pain (0–10)", "0"],
              ] as const
            ).map(([name, label, placeholder]) => (
              <div key={name} className="space-y-1.5">
                <Label className="text-xs">{label}</Label>
                <Input
                  type="number"
                  step="any"
                  placeholder={placeholder}
                  {...form.register(name)}
                />
              </div>
            ))}
          </div>
          <div className="space-y-1.5">
            <Label>Notes</Label>
            <Textarea rows={2} {...form.register("notes")} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={form.handleSubmit((v) => mutation.mutate(v))} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function VitalsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [historyPatient, setHistoryPatient] = useState<string>("");

  const params: Record<string, unknown> = { page };
  if (search) params.search = search;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["vitals", params],
    queryFn: () => api.get<Paginated<VitalSigns>>("/consultations/vitals/", { params }).then((r) => r.data),
  });

  const { data: history } = useQuery({
    queryKey: ["vitals", "history", historyPatient],
    queryFn: () =>
      api
        .get<VitalSigns[]>("/consultations/vitals/history/", { params: { patient: historyPatient } })
        .then((r) => r.data),
    enabled: !!historyPatient,
  });

  const latest = history && history.length > 0 ? history[history.length - 1] : null;

  const columns: ColumnDef<VitalSigns>[] = [
    {
      header: "Patient",
      cell: (v) => (
        <div>
          <p className="font-medium">{v.patient}</p>
        </div>
      ),
    },
    { header: "Temp", cell: (v) => (v.temperature ? `${v.temperature}°C` : "—") },
    {
      header: "BP",
      cell: (v) =>
        v.blood_pressure_systolic && v.blood_pressure_diastolic
          ? `${v.blood_pressure_systolic}/${v.blood_pressure_diastolic}`
          : "—",
    },
    { header: "Pulse", cell: (v) => (v.pulse ? `${v.pulse}` : "—") },
    { header: "Resp", cell: (v) => (v.respiratory_rate ? `${v.respiratory_rate}` : "—") },
    { header: "O₂", cell: (v) => (v.oxygen_saturation ? `${v.oxygen_saturation}%` : "—") },
    { header: "Weight", cell: (v) => (v.weight ? `${v.weight} kg` : "—") },
    { header: "Pain", cell: (v) => (v.pain_score != null ? `${v.pain_score}/10` : "—") },
    {
      header: "Recorded",
      cell: (v) => (
        <div>
          <p>{formatDateTime(v.recorded_at)}</p>
          <p className="text-muted-foreground text-xs">{v.recorded_by_name}</p>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Vital signs" description={`${data?.count?.toLocaleString() ?? 0} readings recorded`}>
        <RecordVitalsDialog />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <DataTable
            columns={columns}
            data={data?.results ?? []}
            loading={isLoading}
            error={isError ? "Unable to load vital signs." : null}
            onRetry={refetch}
            count={data?.count}
            page={data?.page ?? page}
            totalPages={data?.total_pages ?? 1}
            onPageChange={setPage}
            toolbar={
              <SearchInput value={search} onChange={setSearch} placeholder="Search patient…" className="sm:max-w-xs" />
            }
          />
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="size-4 text-primary" /> Vitals history
              </CardTitle>
              <CardDescription>Select a patient ID to chart their vitals trend.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs">Patient</Label>
                <PatientSelect value={historyPatient ? Number(historyPatient) : null} onChange={(id) => setHistoryPatient(id ? String(id) : "")} />
              </div>
              {latest && (
                <div className="bg-muted/50 grid grid-cols-3 gap-2 rounded-lg p-3">
                  {latest.temperature && (
                    <div>
                      <p className="text-muted-foreground text-[10px] uppercase">Temp</p>
                      <p className="text-sm font-semibold">{latest.temperature}°C</p>
                    </div>
                  )}
                  {latest.blood_pressure_systolic && (
                    <div>
                      <p className="text-muted-foreground text-[10px] uppercase">BP</p>
                      <p className="text-sm font-semibold">
                        {latest.blood_pressure_systolic}/{latest.blood_pressure_diastolic}
                      </p>
                    </div>
                  )}
                  {latest.pulse && (
                    <div>
                      <p className="text-muted-foreground text-[10px] uppercase">Pulse</p>
                      <p className="text-sm font-semibold">{latest.pulse}</p>
                    </div>
                  )}
                </div>
              )}
              <div className="space-y-1">
                {(history ?? []).slice(-12).map((v) => (
                  <div key={v.id} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{formatDateTime(v.recorded_at)}</span>
                    <span className="font-medium">
                      {v.blood_pressure_systolic ? `${v.blood_pressure_systolic}/${v.blood_pressure_diastolic}` : ""}
                      {v.pulse ? ` · ${v.pulse} bpm` : ""}
                    </span>
                  </div>
                ))}
                {history && history.length === 0 && (
                  <p className="text-muted-foreground text-sm">No readings for this patient.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
