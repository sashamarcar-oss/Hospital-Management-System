import { CalendarDays, Pencil, Plus, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, getErrorMessage } from "@/lib/api";
import type { Department, NurseShift, Paginated, Staff } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

type ShiftDraft = Pick<NurseShift, "nurse" | "department" | "shift_date" | "start_time" | "end_time" | "shift_type" | "location">;

const dateToday = () => new Date().toISOString().slice(0, 10);

export function ShiftManagementPage() {
  const client = useQueryClient();
  const { can, hasRole } = useAuth();
  const isHospitalManagement = hasRole("admin", "super_admin", "hr");
  const canCreate = isHospitalManagement || can("shifts.create");
  const canUpdate = isHospitalManagement || can("shifts.update");
  const canDelete = isHospitalManagement || can("shifts.delete");
  const { success, error } = useToast();
  const { data = [], isLoading } = useQuery({
    queryKey: ["shifts"],
    queryFn: () => api.get<Paginated<NurseShift>>("/shifts/", { params: { page_size: 100, ordering: "shift_date,start_time" } }).then((r) => r.data.results),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/shifts/${id}/`),
    onSuccess: () => { success("Shift cancelled"); client.invalidateQueries({ queryKey: ["shifts"] }); },
    onError: (e) => error(getErrorMessage(e, "Unable to cancel shift.")),
  });
  const today = dateToday();

  return <div className="space-y-6">
    <PageHeader title="Shift Management" description="Assign staff, monitor coverage, and prevent scheduling conflicts.">
      {canCreate && <ShiftDialog onDone={() => client.invalidateQueries({ queryKey: ["shifts"] })} />}
    </PageHeader>
    <div className="grid gap-4 sm:grid-cols-3">
      <Stat label="Today's shifts" value={data.filter((shift) => shift.shift_date === today && shift.status !== "cancelled").length} />
      <Stat label="Staff on duty" value={data.filter((shift) => shift.effective_status === "active").length} />
      <Stat label="Upcoming" value={data.filter((shift) => shift.effective_status === "scheduled").length} />
    </div>
    <section className="rounded-lg border bg-card">
      <div className="border-b p-4 font-medium">Scheduled shifts</div>
      {isLoading ? <p className="p-5 text-sm text-muted-foreground">Loading…</p> : data.length ? data.map((shift) => <div key={shift.id} className="flex flex-wrap items-center justify-between gap-3 border-b p-4 text-sm last:border-0">
        <div>
          <p className="font-medium">{shift.nurse_details.first_name} {shift.nurse_details.last_name} <span className="font-normal text-muted-foreground">· {shift.department_name || "Department not specified"}</span></p>
          <p className="text-muted-foreground">{shift.shift_date} · {shift.start_time.slice(0, 5)}–{shift.end_time.slice(0, 5)} · {shift.location || "Ward not specified"} · <span className="capitalize">{shift.shift_type} shift</span></p>
        </div>
        <div className="flex items-center gap-2"><span className="text-xs font-medium uppercase text-muted-foreground">{statusLabel(shift.effective_status)}</span>{canUpdate && <ShiftDialog shift={shift} onDone={() => client.invalidateQueries({ queryKey: ["shifts"] })} />}{canDelete && <Button variant="ghost" size="icon" aria-label={`Cancel shift for ${shift.nurse_details.first_name}`} disabled={remove.isPending} onClick={() => remove.mutate(shift.id)}><Trash2 className="size-4 text-destructive" /></Button>}</div>
      </div>) : <p className="p-8 text-center text-sm text-muted-foreground">No shifts scheduled.</p>}
    </section>
  </div>;
}

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border bg-card p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>;
}

function statusLabel(status: string) {
  return status === "active" ? "ON DUTY" : status === "scheduled" ? "UPCOMING" : status.toUpperCase();
}

function ShiftDialog({ shift, onDone }: { shift?: NurseShift; onDone: () => void }) {
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<ShiftDraft>(() => shift ? {
    nurse: shift.nurse, department: shift.department, shift_date: shift.shift_date, start_time: shift.start_time.slice(0, 5), end_time: shift.end_time.slice(0, 5), shift_type: shift.shift_type, location: shift.location,
  } : { nurse: 0, department: null, shift_date: dateToday(), start_time: "08:00", end_time: "16:00", shift_type: "morning", location: "" });
  const { data: staff } = useQuery({ queryKey: ["staff", "shift-assignment"], queryFn: () => api.get<Paginated<Staff>>("/staff/", { params: { page_size: 200 } }).then((r) => r.data) });
  const { data: departments } = useQuery({ queryKey: ["departments"], queryFn: () => api.get<Paginated<Department>>("/departments/", { params: { page_size: 200 } }).then((r) => r.data) });
  const mutation = useMutation({
    mutationFn: () => shift ? api.patch(`/shifts/${shift.id}/`, draft) : api.post("/shifts/", draft),
    onSuccess: () => { success(shift ? "Shift updated" : "Shift assigned"); setOpen(false); onDone(); },
    onError: (e) => error(getErrorMessage(e, shift ? "Unable to update shift." : "Unable to assign shift.")),
  });
  const set = <K extends keyof ShiftDraft>(key: K, value: ShiftDraft[K]) => setDraft((current) => ({ ...current, [key]: value }));
  const availableStaff = (staff?.results ?? []).filter((person) => person.user_details.role_code !== "patient" && person.user_details.is_active);

  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button variant={shift ? "ghost" : "default"} size={shift ? "icon" : "default"} aria-label={shift ? "Edit shift" : undefined}>{shift ? <Pencil className="size-4" /> : <><Plus /> Create Shift</>}</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>{shift ? "Edit shift" : "Assign staff shift"}</DialogTitle></DialogHeader><div className="grid gap-4">
    <div><Label>Staff member</Label><Select value={draft.nurse ? String(draft.nurse) : ""} onValueChange={(value) => set("nurse", Number(value))}><SelectTrigger><SelectValue placeholder="Select staff member" /></SelectTrigger><SelectContent>{availableStaff.map((person) => <SelectItem key={person.id} value={String(person.user)}>{person.user_details.first_name} {person.user_details.last_name}</SelectItem>)}</SelectContent></Select></div>
    <div><Label>Department</Label><Select value={draft.department ? String(draft.department) : "none"} onValueChange={(value) => set("department", value === "none" ? null : Number(value))}><SelectTrigger><SelectValue placeholder="Department not specified" /></SelectTrigger><SelectContent><SelectItem value="none">Department not specified</SelectItem>{(departments?.results ?? []).map((department) => <SelectItem key={department.id} value={String(department.id)}>{department.name}</SelectItem>)}</SelectContent></Select></div>
    <div className="grid grid-cols-3 gap-2"><div><Label>Date</Label><Input type="date" value={draft.shift_date} onChange={(event) => set("shift_date", event.target.value)} /></div><div><Label>Start</Label><Input type="time" value={draft.start_time} onChange={(event) => set("start_time", event.target.value)} /></div><div><Label>End</Label><Input type="time" value={draft.end_time} onChange={(event) => set("end_time", event.target.value)} /></div></div>
    <div><Label>Shift type</Label><Select value={draft.shift_type} onValueChange={(value) => set("shift_type", value)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["morning", "afternoon", "night", "custom"].map((value) => <SelectItem key={value} value={value} className="capitalize">{value}</SelectItem>)}</SelectContent></Select></div>
    <div><Label>Ward / location</Label><Input value={draft.location} onChange={(event) => set("location", event.target.value)} /></div>
  </div><DialogFooter><Button disabled={!draft.nurse || mutation.isPending} onClick={() => mutation.mutate()}><CalendarDays />{shift ? "Save changes" : "Assign shift"}</Button></DialogFooter></DialogContent></Dialog>;
}
