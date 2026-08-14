import { CalendarClock, Circle, MapPin } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NurseShift } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";

type ShiftStatus = "scheduled" | "active" | "completed" | "cancelled" | "missed";

function localDate(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function shiftStatus(shift: NurseShift, now = new Date()): ShiftStatus {
  if (shift.status !== "scheduled") return shift.status as ShiftStatus;
  const start = new Date(`${shift.shift_date}T${shift.start_time}`);
  const end = new Date(`${shift.shift_date}T${shift.end_time}`);
  if (end <= start) end.setDate(end.getDate() + 1);
  if (now >= end) return "completed";
  return now >= start ? "active" : "scheduled";
}

function formatDate(date: string, includeWeekday = false) {
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    weekday: includeWeekday ? "long" : undefined,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function shiftLocation(shift: NurseShift) {
  return [shift.department_name, shift.location].filter(Boolean).join(" · ") || "Ward not specified";
}

export function NurseShiftsPage() {
  const { user } = useAuth();
  const { data = [], isLoading } = useQuery({
    queryKey: ["my-shifts"],
    queryFn: () => api.get<NurseShift[]>("/shifts/my-shifts/").then((r) => r.data),
    refetchInterval: 60_000,
  });
  const today = localDate();
  const activeShift = data.find((shift) => shiftStatus(shift) === "active");
  const todayShift = data.find((shift) => shift.shift_date === today && shift.status !== "cancelled");
  const upcoming = data
    .filter((shift) => shift.status !== "cancelled" && shiftStatus(shift) === "scheduled")
    .sort((a, b) => `${a.shift_date}T${a.start_time}`.localeCompare(`${b.shift_date}T${b.start_time}`));

  return (
    <div className="space-y-6">
      <PageHeader title={user?.role_code === "nurse" ? "My Shifts" : "My Schedule"} description="View your current shift, upcoming schedule, and duty status." />

      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Today's Shift" value={todayShift ? `${todayShift.start_time.slice(0, 5)} – ${todayShift.end_time.slice(0, 5)}` : "No shift scheduled"} />
        <SummaryCard label="Current Status" value={activeShift ? "ON DUTY" : "OFF DUTY"} highlighted={!!activeShift} />
        <SummaryCard label="Upcoming Shifts" value={String(upcoming.length)} />
      </div>

      {activeShift && <section className="rounded-lg border border-primary/30 bg-primary/5 p-5">
        <p className="text-xs font-semibold tracking-wider text-primary uppercase">Current Shift</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          <div><p className="text-2xl font-semibold">{activeShift.start_time.slice(0, 5)} – {activeShift.end_time.slice(0, 5)}</p><p className="mt-1 text-sm text-muted-foreground">{shiftLocation(activeShift)}</p></div>
          <Badge className="gap-1.5"><Circle className="size-2 fill-current" />ON DUTY</Badge>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">{formatDate(activeShift.shift_date, true)}</p>
      </section>}

      <section>
        <h2 className="mb-3 font-semibold">Upcoming Shifts</h2>
        {isLoading ? <p className="text-sm text-muted-foreground">Loading shifts…</p> : upcoming.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{upcoming.map((shift) => <ShiftCard key={shift.id} shift={shift} />)}</div> : <EmptyState message="You currently have no upcoming shifts." />}
      </section>

      {!isLoading && !data.length && <section><h2 className="mb-3 font-semibold">Schedule</h2><EmptyState message="No shifts scheduled" /></section>}
    </div>
  );
}

function SummaryCard({ label, value, highlighted = false }: { label: string; value: string; highlighted?: boolean }) {
  return <div className="rounded-lg border bg-card p-5"><p className="text-sm text-muted-foreground">{label}</p><p className={highlighted ? "mt-3 text-2xl font-semibold text-primary" : "mt-3 text-2xl font-semibold"}>{value}</p></div>;
}

function EmptyState({ message }: { message: string }) {
  return <p className="rounded-lg border p-8 text-center text-sm text-muted-foreground">{message}</p>;
}

function ShiftCard({ shift }: { shift: NurseShift }) {
  const status = shiftStatus(shift);
  const label = status === "active" ? "ON DUTY" : status === "scheduled" ? "UPCOMING" : status.toUpperCase();
  return <article className="rounded-lg border bg-card p-4"><div className="flex items-start justify-between gap-2"><div><p className="font-medium">{formatDate(shift.shift_date)}</p><p className="mt-1 text-sm text-muted-foreground capitalize">{shift.shift_type} shift</p></div><Badge variant={status === "cancelled" ? "destructive" : "secondary"} className="capitalize">{label}</Badge></div><p className="mt-4 flex items-center gap-2 text-sm"><CalendarClock className="size-4" />{shift.start_time.slice(0, 5)} – {shift.end_time.slice(0, 5)}</p><p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground"><MapPin className="size-4 shrink-0" />{shiftLocation(shift)}</p></article>;
}
