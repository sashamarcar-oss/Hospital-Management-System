import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Consultation, LabTestCatalog, Medicine, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Checkbox } from "@/components/ui/checkbox";
import { PatientSelect } from "@/components/common/patient-select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { handleMutationError } from "@/lib/mutation-error";
import { RADIOLOGY_PROCEDURES, RADIOLOGY_PROCEDURE_LABELS } from "@/lib/constants";

const diagnosisSchema = z.object({
  icd_code: z.string().optional(),
  name: z.string().min(1, "Diagnosis name is required"),
  description: z.string().optional(),
});

const prescriptionItemSchema = z.object({
  medicine: z.number({ message: "Select a medicine" }),
  dosage: z.string().min(1, "Dosage is required"),
  frequency: z.string().min(1, "Frequency is required"),
  duration: z.string().min(1, "Duration is required"),
  route: z.string().default("oral"),
  quantity: z.coerce.number().min(1, "Quantity must be at least 1"),
  instructions: z.string().optional(),
});

const consultationSchema = z.object({
  patient: z.number({ message: "Select a patient" }),
  chief_complaint: z.string().min(1, "Chief complaint is required"),
  history_of_presenting_illness: z.string().optional(),
  symptoms: z.string().optional(),
  physical_examination: z.string().optional(),
  clinical_notes: z.string().optional(),
  treatment_plan: z.string().optional(),
  procedures: z.string().optional(),
  follow_up_date: z.string().optional().nullable(),
  status: z.enum(["in_progress", "completed"]).default("in_progress"),
  vitals: z
    .object({
      temperature: z.string().optional().nullable(),
      blood_pressure_systolic: z.coerce.number().nullable().optional(),
      blood_pressure_diastolic: z.coerce.number().nullable().optional(),
      pulse: z.coerce.number().nullable().optional(),
      respiratory_rate: z.coerce.number().nullable().optional(),
      oxygen_saturation: z.coerce.number().nullable().optional(),
      weight: z.string().optional().nullable(),
      height: z.string().optional().nullable(),
      pain_score: z.coerce.number().nullable().optional(),
    })
    .optional(),
  diagnoses: z.array(diagnosisSchema).min(1, "Add at least one diagnosis"),
  prescriptions: z.array(prescriptionItemSchema).optional(),
  lab_tests: z.array(z.number()).optional(),
  lab_notes: z.string().optional(),
  radiology: z
    .object({
      procedure_type: z.string().optional(),
      body_part: z.string().optional(),
      clinical_indication: z.string().optional(),
    })
    .optional(),
});

type ConsultationForm = z.infer<typeof consultationSchema>;

export function ConsultationNewPage() {
  const { success } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const initialPatientId = searchParams.get("patient") ? Number(searchParams.get("patient")) : undefined;

  const { data: medicineCatalog } = useQuery({
    queryKey: ["pharmacy", "medicines", "all"],
    queryFn: () =>
      api.get<Paginated<Medicine>>("/pharmacy/medicines/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const { data: labCatalog } = useQuery({
    queryKey: ["laboratory", "catalog"],
    queryFn: () =>
      api.get<Paginated<LabTestCatalog>>("/laboratory/catalog/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const form = useForm<ConsultationForm>({
    resolver: zodResolver(consultationSchema),
    defaultValues: {
      patient: initialPatientId ?? (undefined as unknown as number),
      chief_complaint: "",
      history_of_presenting_illness: "",
      symptoms: "",
      physical_examination: "",
      clinical_notes: "",
      treatment_plan: "",
      procedures: "",
      follow_up_date: null,
      status: "in_progress",
      vitals: {
        temperature: "",
        blood_pressure_systolic: null,
        blood_pressure_diastolic: null,
        pulse: null,
        respiratory_rate: null,
        oxygen_saturation: null,
        weight: "",
        height: "",
        pain_score: null,
      },
      diagnoses: [{ icd_code: "", name: "", description: "" }],
      prescriptions: [],
      lab_tests: [],
      lab_notes: "",
      radiology: { procedure_type: "", body_part: "", clinical_indication: "" },
    },
  });

  const {
    fields: diagnosisFields,
    append: appendDiagnosis,
    remove: removeDiagnosis,
  } = useFieldArray({
    control: form.control,
    name: "diagnoses",
  });

  const {
    fields: prescriptionFields,
    append: appendPrescription,
    remove: removePrescription,
  } = useFieldArray({
    control: form.control,
    name: "prescriptions",
  });

  const patientWatch = form.watch("patient");
  const labTestsWatch = form.watch("lab_tests") ?? [];

  const mutation = useMutation({
    mutationFn: async (values: ConsultationForm) => {
      const vitals = values.vitals ?? {};
      const vitalsPresent = Object.values(vitals).some(
        (v) => v !== null && v !== "" && v !== undefined
      );
      const consultation = await api
        .post<Consultation>("/consultations/", {
          ...values,
          doctor: user?.id,
          vital_signs: vitalsPresent
            ? [
                Object.fromEntries(
                  Object.entries(vitals).filter(([, v]) => v !== null && v !== "" && v !== undefined)
                ),
              ]
            : [],
          diagnoses: values.diagnoses.map((d, index) => ({ ...d, is_primary: index === 0 })),
        })
        .then((r) => r.data);

      const orders: Promise<unknown>[] = [];

      if (values.prescriptions?.length) {
        orders.push(
          api.post("/consultations/prescriptions/", {
            patient: values.patient,
            doctor: user?.id,
            consultation: consultation.id,
            status: "active",
            items: values.prescriptions.map((p) => ({
              medicine: p.medicine,
              dosage: p.dosage,
              frequency: p.frequency,
              duration: p.duration,
              route: p.route ?? "oral",
              quantity: p.quantity,
              instructions: p.instructions ?? "",
            })),
          })
        );
      }

      if (values.lab_tests?.length) {
        orders.push(
          api.post(`/consultations/${consultation.id}/request_lab/`, {
            tests: values.lab_tests,
            priority: "routine",
          })
        );
      }

      if (values.radiology?.procedure_type) {
        orders.push(
          api.post("/radiology/", {
            patient: values.patient,
            doctor: user?.id,
            consultation: consultation.id,
            procedure_type: values.radiology.procedure_type,
            body_part: values.radiology.body_part ?? "",
            clinical_indication: values.radiology.clinical_indication ?? "",
            priority: "routine",
          })
        );
      }

      await Promise.all(orders);
      return consultation;
    },
    onSuccess: (consultation) => {
      queryClient.invalidateQueries({ queryKey: ["consultations"] });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      success("Consultation saved", "Clinical record created successfully.");
      navigate(`/consultations/${consultation.id}`);
    },
    onError: (err) =>
      handleMutationError(err, "Unable to save consultation. Please check the form and try again.", (fieldErrors) => {
        Object.entries(fieldErrors).forEach(([k, v]) => {
          const field = k as keyof ConsultationForm;
          if (field in form.getValues()) form.setError(field, { message: v });
        });
      }),
  });

  const onSubmit = (values: ConsultationForm) => mutation.mutate(values);

  return (
    <div className="space-y-6">
      <PageHeader title="New consultation" description={`Clinician: Dr. ${user?.first_name} ${user?.last_name}`} />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Patient</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <FormLabel>
                  Patient <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <PatientSelect
                    value={patientWatch ?? null}
                    onChange={(id) => form.setValue("patient", id ?? (undefined as unknown as number))}
                  />
                </FormControl>
                {form.formState.errors.patient && (
                  <p className="text-destructive text-sm">{form.formState.errors.patient.message}</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Clinical information</CardTitle>
              <CardDescription>Chief complaint, history and examination</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="chief_complaint"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Chief complaint <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Persistent headache and dizziness" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid gap-4 lg:grid-cols-2">
                <FormField
                  control={form.control}
                  name="history_of_presenting_illness"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>History of presenting illness</FormLabel>
                      <FormControl>
                        <Textarea rows={4} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="symptoms"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Symptoms</FormLabel>
                      <FormControl>
                        <Textarea rows={4} placeholder="Comma-separated symptoms…" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="physical_examination"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Physical examination</FormLabel>
                    <FormControl>
                      <Textarea rows={3} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="clinical_notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Clinical notes</FormLabel>
                    <FormControl>
                      <Textarea rows={3} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Vital signs</CardTitle>
              <CardDescription>Optional — can also be recorded by nursing staff</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              <FormField
                control={form.control}
                name="vitals.temperature"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Temperature (°C)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.blood_pressure_systolic"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>BP systolic</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.blood_pressure_diastolic"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>BP diastolic</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.pulse"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pulse (bpm)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.respiratory_rate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Resp rate</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.oxygen_saturation"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>O₂ (%)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.weight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Weight (kg)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.height"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Height (cm)</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" {...field} value={field.value ?? ""} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="vitals.pain_score"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pain (0–10)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        max={10}
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Diagnoses</CardTitle>
                <CardDescription>Add primary and secondary diagnoses (ICD-10 codes where available)</CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => appendDiagnosis({ icd_code: "", name: "", description: "" })}
              >
                <Plus /> Add diagnosis
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {diagnosisFields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid gap-3 rounded-lg border p-3 sm:grid-cols-[120px_1fr_1fr_auto]"
                >
                  <FormField
                    control={form.control}
                    name={`diagnoses.${index}.icd_code`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>ICD-10</FormLabel>
                        <FormControl>
                          <Input placeholder="I10" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`diagnoses.${index}.name`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Diagnosis <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="e.g. Essential hypertension" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`diagnoses.${index}.description`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="mt-6"
                    disabled={diagnosisFields.length === 1}
                    onClick={() => removeDiagnosis(index)}
                  >
                    <Trash2 className="text-destructive" />
                  </Button>
                </div>
              ))}
              {form.formState.errors.diagnoses?.message && (
                <p className="text-destructive text-sm">{form.formState.errors.diagnoses.message}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle>Prescriptions</CardTitle>
                <CardDescription>Medication orders for this consultation — sent to the pharmacy</CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  appendPrescription({
                    medicine: undefined as unknown as number,
                    dosage: "",
                    frequency: "",
                    duration: "",
                    route: "oral",
                    quantity: 1,
                    instructions: "",
                  })
                }
              >
                <Plus /> Add medicine
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {prescriptionFields.length === 0 && (
                <p className="text-muted-foreground text-sm">
                  No medicines prescribed. Add a prescription to send it to the pharmacy.
                </p>
              )}
              {prescriptionFields.map((field, index) => (
                <div
                  key={field.id}
                  className="grid gap-3 rounded-lg border p-3 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr_0.8fr_0.7fr_auto]"
                >
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.medicine`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Medicine <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Select
                            value={field.value ? String(field.value) : ""}
                            onValueChange={(v) => field.onChange(Number(v))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select medicine" />
                            </SelectTrigger>
                            <SelectContent>
                              {(medicineCatalog?.results ?? []).map((m) => (
                                <SelectItem key={m.id} value={String(m.id)}>
                                  {m.name} {m.strength ? `(${m.strength})` : ""} — stock {m.total_stock}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.dosage`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Dosage <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="500mg" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.frequency`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Frequency <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="3x daily" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.duration`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Duration <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="7 days" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.route`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Route</FormLabel>
                        <FormControl>
                          <Select value={field.value} onValueChange={field.onChange}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {["oral", "iv", "im", "sc", "topical", "inhaled", "rectal"].map((r) => (
                                <SelectItem key={r} value={r}>
                                  {r.toUpperCase()}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name={`prescriptions.${index}.quantity`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Qty <span className="text-red-500">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            {...field}
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="lg:mt-6"
                    onClick={() => removePrescription(index)}
                  >
                    <Trash2 className="text-destructive" />
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Laboratory requests</CardTitle>
              <CardDescription>Order lab tests — results return to this patient's record</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(labCatalog?.results ?? []).map((t) => (
                  <label
                    key={t.id}
                    className="hover:bg-muted/40 flex cursor-pointer items-start gap-2 rounded-md border p-2.5"
                  >
                    <Checkbox
                      checked={labTestsWatch.includes(t.id)}
                      onCheckedChange={(checked) => {
                        const current = labTestsWatch;
                        form.setValue(
                          "lab_tests",
                          checked ? [...current, t.id] : current.filter((id) => id !== t.id)
                        );
                      }}
                    />
                    <div>
                      <p className="text-sm font-medium">{t.name}</p>
                      <p className="text-muted-foreground text-xs">
                        {t.category} · {t.sample_type}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
              <FormField
                control={form.control}
                name="lab_notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Clinical notes for lab</FormLabel>
                    <FormControl>
                      <Textarea rows={2} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Imaging request</CardTitle>
              <CardDescription>Optional radiology order</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <FormField
                control={form.control}
                name="radiology.procedure_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Procedure</FormLabel>
                    <FormControl>
                      <Select value={field.value ?? ""} onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select procedure" />
                        </SelectTrigger>
                        <SelectContent>
                          {RADIOLOGY_PROCEDURES.map((p) => (
                            <SelectItem key={p} value={p}>
                              {RADIOLOGY_PROCEDURE_LABELS[p]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="radiology.body_part"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Body part</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Chest, Left knee" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="radiology.clinical_indication"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Clinical indication</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Treatment & follow-up</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-2">
                <FormField
                  control={form.control}
                  name="treatment_plan"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Treatment plan</FormLabel>
                      <FormControl>
                        <Textarea rows={3} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="procedures"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Procedures performed</FormLabel>
                      <FormControl>
                        <Textarea rows={3} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="follow_up_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Follow-up date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} value={field.value ?? ""} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Status</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="in_progress">In Progress</SelectItem>
                            <SelectItem value="completed">Completed</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              Save consultation
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
