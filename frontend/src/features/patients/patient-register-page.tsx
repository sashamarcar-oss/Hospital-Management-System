import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { handleMutationError } from "@/lib/mutation-error";
import type { Patient } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BLOOD_GROUPS, GENDER_LABELS, MARITAL_LABELS } from "@/lib/constants";

const patientSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  middle_name: z.string().optional(),
  last_name: z.string().min(1, "Last name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  gender: z.enum(["male", "female", "other"], { message: "Select a gender" }),
  national_id: z.string().optional(),
  phone: z.string().min(7, "Enter a valid phone number").optional().or(z.literal("")),
  email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  address: z.string().optional(),
  occupation: z.string().optional(),
  marital_status: z.string().optional(),
  blood_group: z.string().optional(),
  allergies: z.string().optional(),
  insurance_provider: z.string().optional(),
  insurance_number: z.string().optional(),
  next_of_kin_name: z.string().optional(),
  next_of_kin_phone: z.string().optional(),
  next_of_kin_relationship: z.string().optional(),
  emergency_contacts: z
    .array(
      z.object({
        name: z.string().min(1, "Name is required"),
        phone: z.string().min(7, "Phone is required"),
        relationship: z.string().min(1, "Relationship is required"),
        address: z.string().optional(),
      })
    )
    .optional(),
});

type PatientForm = z.infer<typeof patientSchema>;

export function PatientRegisterPage() {
  const { success, error } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const form = useForm<PatientForm>({
    resolver: zodResolver(patientSchema),
    defaultValues: {
      first_name: "",
      middle_name: "",
      last_name: "",
      date_of_birth: "",
      gender: undefined,
      national_id: "",
      phone: "",
      email: "",
      address: "",
      occupation: "",
      marital_status: "single",
      blood_group: "unknown",
      allergies: "",
      insurance_provider: "",
      insurance_number: "",
      next_of_kin_name: "",
      next_of_kin_phone: "",
      next_of_kin_relationship: "",
      emergency_contacts: [],
    },
  });

  const mutation = useMutation({
    mutationFn: (values: PatientForm) => api.post<Patient>("/patients/", values).then((r) => r.data),
    onSuccess: (patient) => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
      success("Patient registered", `Record ${patient.patient_number} created successfully.`);
      navigate(`/patients/${patient.id}`);
    },
    onError: (err) => handleMutationError(err, "Unable to save patient information. Please check the highlighted fields and try again.", (fieldErrors) => {
      Object.entries(fieldErrors).forEach(([k, v]) => {
        const field = k as keyof PatientForm;
        if (field in form.getValues()) {
          form.setError(field, { message: v });
        }
      });
      if (!Object.keys(fieldErrors).some((k) => k in form.getValues())) {
        error("Unable to save patient information. Please check the highlighted fields and try again.");
      }
    }),
  });

  const onSubmit = (values: PatientForm) => {
    mutation.mutate({
      ...values,
      middle_name: values.middle_name ?? "",
      emergency_contacts: values.emergency_contacts ?? [],
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Register new patient"
        description="A unique medical record number will be generated automatically."
      />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Personal information</CardTitle>
              <CardDescription>Basic identification details</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <FormField control={form.control} name="first_name" render={({ field }) => (
                <FormItem><FormLabel>First name <span className="text-red-500">*</span></FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="middle_name" render={({ field }) => (
                <FormItem><FormLabel>Middle name</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="last_name" render={({ field }) => (
                <FormItem><FormLabel>Last name <span className="text-red-500">*</span></FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="date_of_birth" render={({ field }) => (
                <FormItem><FormLabel>Date of birth <span className="text-red-500">*</span></FormLabel><FormControl><Input type="date" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="gender" render={({ field }) => (
                <FormItem>
                  <FormLabel>Gender <span className="text-red-500">*</span></FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger><SelectValue placeholder="Select gender" /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(GENDER_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="national_id" render={({ field }) => (
                <FormItem><FormLabel>National ID / Passport</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="phone" render={({ field }) => (
                <FormItem><FormLabel>Phone</FormLabel><FormControl><Input placeholder="+1 555 000 0000" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="email" render={({ field }) => (
                <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="marital_status" render={({ field }) => (
                <FormItem>
                  <FormLabel>Marital status</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(MARITAL_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="blood_group" render={({ field }) => (
                <FormItem>
                  <FormLabel>Blood group</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {BLOOD_GROUPS.map((bg) => <SelectItem key={bg} value={bg}>{bg === "unknown" ? "Unknown" : bg}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="occupation" render={({ field }) => (
                <FormItem><FormLabel>Occupation</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Contact & medical</CardTitle>
              <CardDescription>Address, allergies and insurance details</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <FormField control={form.control} name="address" render={({ field }) => (
                <FormItem className="sm:col-span-2"><FormLabel>Address</FormLabel><FormControl><Textarea rows={2} {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="allergies" render={({ field }) => (
                <FormItem><FormLabel>Allergies</FormLabel><FormControl><Textarea rows={2} placeholder="e.g. penicillin, peanuts…" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="insurance_provider" render={({ field }) => (
                <FormItem><FormLabel>Insurance provider</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="insurance_number" render={({ field }) => (
                <FormItem><FormLabel>Insurance number</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next of kin</CardTitle>
              <CardDescription>Emergency contact information</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              <FormField control={form.control} name="next_of_kin_name" render={({ field }) => (
                <FormItem><FormLabel>Name</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="next_of_kin_phone" render={({ field }) => (
                <FormItem><FormLabel>Phone</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="next_of_kin_relationship" render={({ field }) => (
                <FormItem><FormLabel>Relationship</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending && <Loader2 className="animate-spin" />}
              Register patient
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
