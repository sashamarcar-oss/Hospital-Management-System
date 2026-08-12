import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Appointment, Department, Paginated, UserBrief } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";
import { handleMutationError } from "@/lib/mutation-error";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PatientSelect } from "@/components/common/patient-select";
import { PRIORITIES, PRIORITY_LABELS } from "@/lib/constants";

const schema = z
  .object({
    patient: z.number({ message: "Select a patient" }),
    doctor: z.number({ message: "Select a doctor" }),
    department: z.number({ message: "Select a department" }),
    appointment_date: z.string().min(1, "Date is required"),
    start_time: z.string().min(1, "Start time is required"),
    end_time: z.string().min(1, "End time is required"),
    reason: z.string().min(1, "Reason is required"),
    priority: z.string().default("routine"),
    notes: z.string().optional(),
  })
  .refine((d) => !d.start_time || !d.end_time || d.end_time > d.start_time, {
    message: "End time must be after start time",
    path: ["end_time"],
  });

type AppointmentForm = z.infer<typeof schema>;

export function AppointmentBookingForm({
  initialPatientId,
  onSuccess,
  onCancel,
}: {
  initialPatientId?: number;
  onSuccess?: (appointment: Appointment) => void;
  onCancel?: () => void;
}) {
  const { success } = useToast();
  const queryClient = useQueryClient();

  const form = useForm<AppointmentForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      patient: initialPatientId ?? (undefined as unknown as number),
      doctor: undefined as unknown as number,
      department: undefined as unknown as number,
      appointment_date: "",
      start_time: "",
      end_time: "",
      reason: "",
      priority: "routine",
      notes: "",
    },
  });

  const patientId = form.watch("patient") as number | undefined;
  const departmentId = form.watch("department") as number | undefined;

  useEffect(() => {
    if (initialPatientId) form.setValue("patient", initialPatientId);
  }, [initialPatientId, form]);

  const { data: departments } = useQuery({
    queryKey: ["departments", "active"],
    queryFn: () =>
      api
        .get<Paginated<Department>>("/departments/", { params: { active: true, page_size: 100 } })
        .then((r) => r.data),
  });

  const { data: doctors, isLoading: isLoadingDoctors, isError: isDoctorsError } = useQuery({
    queryKey: ["users", "doctors"],
    queryFn: () => api.get<UserBrief[]>("/users/doctors/").then((r) => r.data),
  });

  const {
    data: departmentDoctors,
    isLoading: isLoadingDepartmentDoctors,
    isError: isDepartmentDoctorsError,
  } = useQuery({
    queryKey: ["users", "doctors", "department", departmentId],
    queryFn: () =>
      api
        .get<UserBrief[]>("/users/doctors/", { params: { department: departmentId } })
        .then((r) => r.data),
    enabled: !!departmentId,
  });

  const availableDoctors = departmentId ? departmentDoctors ?? [] : doctors ?? [];
  const isLoadingAvailableDoctors = departmentId ? isLoadingDepartmentDoctors : isLoadingDoctors;
  const hasDoctorsError = departmentId ? isDepartmentDoctorsError : isDoctorsError;

  const mutation = useMutation({
    mutationFn: (values: AppointmentForm) =>
      api
        .post<Appointment>("/appointments/", values)
        .then((r) => r.data),
    onSuccess: (appointment) => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      success("Appointment booked", `Reference #${appointment.id} created.`);
      onSuccess?.(appointment);
    },
    onError: (err) =>
      handleMutationError(err, "Unable to book appointment. Please check the form and try again.", (fieldErrors) => {
        Object.entries(fieldErrors).forEach(([k, v]) => {
          const field = k as keyof AppointmentForm;
          if (field in form.getValues()) form.setError(field, { message: v });
        });
      }),
  });

  const onSubmit = (values: AppointmentForm) => mutation.mutate(values);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <div className="space-y-2">
          <FormLabel>Patient</FormLabel>
          <FormControl>
            <PatientSelect
              value={patientId ?? null}
              onChange={(id) => form.setValue("patient", id ?? (undefined as unknown as number))}
            />
          </FormControl>
          {form.formState.errors.patient && (
            <p className="text-destructive text-sm">{form.formState.errors.patient.message}</p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="department"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Department</FormLabel>
                <FormControl>
                  <Select
                    value={field.value ? String(field.value) : ""}
                    onValueChange={(v) => {
                      field.onChange(v ? Number(v) : undefined);
                      form.setValue("doctor", undefined as unknown as number);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select department" />
                    </SelectTrigger>
                    <SelectContent>
                      {(departments?.results ?? []).map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>
                          {d.name}
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
            name="doctor"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Doctor</FormLabel>
                <FormControl>
                  <Select
                    value={field.value ? String(field.value) : ""}
                    onValueChange={(v) => field.onChange(v ? Number(v) : undefined)}
                    disabled={isLoadingAvailableDoctors || hasDoctorsError}
                  >
                    <SelectTrigger>
                      <SelectValue
                        placeholder={
                          isLoadingAvailableDoctors
                            ? "Loading doctors..."
                            : hasDoctorsError
                              ? "Unable to load doctors"
                              : "Select doctor"
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {availableDoctors.map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>
                          Dr. {d.first_name} {d.last_name}
                        </SelectItem>
                      ))}
                      {!isLoadingAvailableDoctors && !hasDoctorsError && availableDoctors.length === 0 && (
                        <SelectItem value="__none__" disabled>
                          No doctors available{departmentId ? " in this department" : ""}
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField
            control={form.control}
            name="appointment_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Date <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Input type="date" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="start_time"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Start time <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Input type="time" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="end_time"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  End time <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Input type="time" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="reason"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Reason <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Input placeholder="e.g. Follow-up on hypertension" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="priority"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Priority</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
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
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea rows={2} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-3">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            Book appointment
          </Button>
        </div>
      </form>
    </Form>
  );
}
