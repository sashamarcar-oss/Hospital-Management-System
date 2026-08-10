import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import type { Appointment } from "@/lib/types";
import {
  addDays,
  addMonths,
  format,
  isSameDay,
  isSameMonth,
  parseISO,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { APPOINTMENT_STATUS_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";

const STATUS_DOT: Record<string, string> = {
  scheduled: "bg-sky-500",
  confirmed: "bg-teal-500",
  checked_in: "bg-amber-500",
  completed: "bg-emerald-500",
  cancelled: "bg-red-400",
  no_show: "bg-slate-400",
};

type ViewMode = "month" | "week" | "day";

export function AppointmentCalendarPage() {
  const [view, setView] = useState<ViewMode>("month");
  const [current, setCurrent] = useState(new Date());

  const { data: appointments } = useQuery({
    queryKey: ["appointments", "calendar", format(current, "yyyy-MM")],
    queryFn: () =>
      api
        .get<Appointment[]>("/appointments/calendar/", {
          params: { year: current.getFullYear(), month: current.getMonth() + 1 },
        })
        .then((r) => r.data),
  });

  const all = appointments ?? [];

  const navigate = (dir: 1 | -1) => {
    if (view === "month") setCurrent((c) => addMonths(c, dir));
    else if (view === "week") setCurrent((c) => addDays(c, dir * 7));
    else setCurrent((c) => addDays(c, dir));
  };

  const weekStart = startOfWeek(current, { weekStartsOn: 1 });
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const dayCells: Date[] =
    view === "month"
      ? Array.from({ length: 42 }, (_, i) => addDays(startOfWeek(startOfMonth(current), { weekStartsOn: 1 }), i))
      : view === "week"
        ? weekDays
        : [current];

  const byDay = (date: Date) => all.filter((a) => isSameDay(parseISO(a.appointment_date), date));

  const title =
    view === "month"
      ? format(current, "MMMM yyyy")
      : view === "week"
        ? `${format(weekStart, "MMM d")} – ${format(addDays(weekStart, 6), "MMM d, yyyy")}`
        : format(current, "EEEE, MMMM d, yyyy");

  return (
    <div className="space-y-6">
      <PageHeader title="Appointment calendar" description="View appointments by day, week or month.">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigate(-1)}>
            <ChevronLeft />
          </Button>
          <Button variant="outline" onClick={() => setCurrent(new Date())}>
            Today
          </Button>
          <Button variant="outline" size="icon" onClick={() => navigate(1)}>
            <ChevronRight />
          </Button>
        </div>
        <div className="flex rounded-md border">
          {(["month", "week", "day"] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                "px-3 py-1.5 text-sm capitalize transition-colors",
                view === v ? "bg-primary text-primary-foreground" : "hover:bg-accent"
              )}
            >
              {v}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <CalendarDays className="size-5 text-primary" />
            {title}
          </h2>
        </div>
        <div className="grid grid-cols-7 border-b bg-muted/40">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => (
            <div
              key={d}
              className={cn(
                "text-muted-foreground px-3 py-2 text-xs font-medium",
                i < 6 && "border-r"
              )}
            >
              {d}
            </div>
          ))}
        </div>
        <div className={cn("grid", view === "day" ? "grid-cols-1" : "grid-cols-7")}>
          {dayCells.map((day, i) => {
            const dayAppointments = byDay(day);
            const isToday = isSameDay(day, new Date());
            return (
              <div
                key={i}
                className={cn(
                  "min-h-28 border-b p-2",
                  view !== "day" && i % 7 !== 6 && "border-r",
                  view === "day" && "min-h-72",
                  !isSameMonth(day, current) && "bg-muted/30",
                  isToday && "bg-teal-50/60 dark:bg-teal-500/15"
                )}
              >
                <div className="mb-1.5 flex items-center justify-between">
                  <span
                    className={cn(
                      "text-xs font-medium",
                      isToday
                        ? "bg-primary flex size-6 items-center justify-center rounded-full text-primary-foreground"
                        : "text-muted-foreground"
                    )}
                  >
                    {format(day, "d")}
                  </span>
                  {dayAppointments.length > 0 && (
                    <span className="text-muted-foreground text-[10px]">{dayAppointments.length}</span>
                  )}
                </div>
                <div className="space-y-1">
                  {dayAppointments.slice(0, 3).map((a) => (
                    <Link key={a.id} to={`/patients/${a.patient}`}>
                      <div
                        className="hover:bg-slate-100 rounded bg-slate-50 px-1.5 py-1 text-[10px] leading-tight dark:bg-slate-500/15 dark:hover:bg-slate-500/25"
                        title={`${a.patient_details?.full_name} — ${a.reason || ""}`}
                      >
                        <span className={cn("mr-1 inline-block size-1.5 rounded-full", STATUS_DOT[a.status] ?? "bg-slate-300")} />
                        <span className="font-medium">{a.patient_details?.full_name}</span>
                      </div>
                    </Link>
                  ))}
                  {dayAppointments.length > 3 && (
                    <p className="text-muted-foreground px-1 text-[10px]">+{dayAppointments.length - 3} more</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        {Object.entries(APPOINTMENT_STATUS_LABELS).map(([k, v]) => (
          <span key={k} className="text-muted-foreground flex items-center gap-1.5 text-xs">
            <span className={cn("size-2 rounded-full", STATUS_DOT[k])} /> {v}
          </span>
        ))}
      </div>
    </div>
  );
}
