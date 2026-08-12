import { CalendarClock, MapPin } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NurseShift } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";

export function NurseShiftsPage() {
  const { data = [], isLoading } = useQuery({ queryKey: ["my-shifts"], queryFn: () => api.get<NurseShift[]>("/shifts/my-shifts/").then(r => r.data) });
  const today = new Date().toISOString().slice(0, 10);
  const todays = data.filter(s => s.shift_date === today);
  return <div className="space-y-6"><PageHeader title="My shifts" description="Your assigned schedule and upcoming clinical coverage." />
    <div className="grid gap-4 md:grid-cols-3"><div className="rounded-lg border bg-card p-5 md:col-span-2"><p className="text-sm text-muted-foreground">Today's shift</p>{todays[0] ? <ShiftCard shift={todays[0]} /> : <p className="mt-5 text-sm text-muted-foreground">No shift scheduled today.</p>}</div><div className="rounded-lg border bg-card p-5"><p className="text-sm text-muted-foreground">Upcoming shifts</p><p className="mt-3 text-3xl font-semibold">{data.filter(s => s.shift_date >= today && s.status !== "cancelled").length}</p><p className="text-xs text-muted-foreground">assigned shifts</p></div></div>
    <section><h2 className="mb-3 font-semibold">Schedule</h2>{isLoading ? <p className="text-sm text-muted-foreground">Loading shifts…</p> : data.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{data.map(s => <ShiftCard key={s.id} shift={s} />)}</div> : <p className="rounded-lg border p-8 text-center text-sm text-muted-foreground">Your shift calendar is clear.</p>}</section></div>
}
function ShiftCard({ shift }: { shift: NurseShift }) { const status = shift.effective_status || shift.status; return <div className="mt-3 rounded-lg border p-4"><div className="flex items-start justify-between gap-2"><div><p className="font-medium capitalize">{shift.shift_type} shift</p><p className="text-sm text-muted-foreground">{new Date(`${shift.shift_date}T00:00:00`).toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"})}</p></div><Badge variant={status === "cancelled" ? "destructive" : "secondary"} className="capitalize">{status}</Badge></div><p className="mt-3 flex items-center gap-2 text-sm"><CalendarClock className="size-4" />{shift.start_time.slice(0,5)} – {shift.end_time.slice(0,5)}</p><p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground"><MapPin className="size-4" />{shift.department_name || "No department"}{shift.location ? ` · ${shift.location}` : ""}</p></div> }
