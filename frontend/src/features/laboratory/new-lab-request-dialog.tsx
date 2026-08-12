import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { LabTestCatalog, Paginated } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { handleMutationError } from "@/lib/mutation-error";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { PatientSelect } from "@/components/common/patient-select";
import { PRIORITIES, PRIORITY_LABELS } from "@/lib/constants";
import { LAB_CATEGORY_LABELS } from "@/lib/constants";

export function NewLabRequestDialog({ defaultPatientId }: { defaultPatientId?: number }) {
  const { success } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [patient, setPatient] = useState<number | null>(defaultPatientId ?? null);
  const [priority, setPriority] = useState("routine");
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [category, setCategory] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const {
    data: catalog,
    isLoading: isLoadingCatalog,
    isError: isCatalogError,
  } = useQuery({
    queryKey: ["laboratory", "catalog", category],
    queryFn: () =>
      api
        .get<Paginated<LabTestCatalog>>("/laboratory/catalog/", {
          params: { page_size: 200, category: category || undefined },
        })
        .then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/laboratory/", {
        patient,
        doctor: user?.id,
        priority,
        clinical_notes: clinicalNotes,
        test_ids: selected,
      }),
    onSuccess: () => {
      success("Lab request created");
      setOpen(false);
      setSelected([]);
      setClinicalNotes("");
      setFieldErrors({});
      queryClient.invalidateQueries({ queryKey: ["laboratory"] });
    },
    onError: (err) =>
      handleMutationError(err, "Unable to create lab request.", setFieldErrors),
  });

  const submit = () => {
    const errors: Record<string, string> = {};
    if (!patient) errors.patient = "Select a patient";
    if (selected.length === 0) errors.test_ids = "Select at least one test";
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New lab request
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>New laboratory request</DialogTitle>
          <DialogDescription>Select the patient and the tests to be performed.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>
              Patient <span className="text-red-500">*</span>
            </Label>
            <PatientSelect value={patient} onChange={setPatient} />
            {fieldErrors.patient && <p className="text-destructive text-sm">{fieldErrors.patient}</p>}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {PRIORITY_LABELS[p]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Test category</Label>
              <Select
                value={category || "all"}
                onValueChange={(value) => setCategory(value === "all" ? "" : value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All categories</SelectItem>
                  {Object.entries(LAB_CATEGORY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>Clinical notes</Label>
            <Textarea rows={2} value={clinicalNotes} onChange={(e) => setClinicalNotes(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>
              Tests <span className="text-red-500">*</span>
            </Label>
            <div className="border-input bg-muted/20 max-h-52 space-y-1.5 overflow-y-auto rounded-md border p-2">
              {isLoadingCatalog && (
                <p className="text-muted-foreground py-3 text-center text-sm">Loading test catalog...</p>
              )}
              {isCatalogError && (
                <p className="text-destructive py-3 text-center text-sm">
                  Unable to load tests. Please check the server connection and try again.
                </p>
              )}
              {(catalog?.results ?? []).map((t) => (
                <label key={t.id} className="hover:bg-muted/60 flex cursor-pointer items-start gap-2 rounded p-1.5">
                  <Checkbox
                    checked={selected.includes(t.id)}
                    onCheckedChange={(checked) =>
                      setSelected((prev) => (checked ? [...prev, t.id] : prev.filter((id) => id !== t.id)))
                    }
                  />
                  <div>
                    <p className="text-sm font-medium">{t.name}</p>
                    <p className="text-muted-foreground text-xs">
                      {LAB_CATEGORY_LABELS[t.category] ?? t.category} · {t.sample_type}
                    </p>
                  </div>
                </label>
              ))}
              {!isLoadingCatalog && !isCatalogError && catalog && catalog.results.length === 0 && (
                <p className="text-muted-foreground text-center text-sm">No tests in this category.</p>
              )}
            </div>
            {fieldErrors.test_ids && <p className="text-destructive text-sm">{fieldErrors.test_ids}</p>}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Create request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
