import { useState } from "react";
import { CalendarCheck, Clock, Loader2, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Attendance, Paginated, Staff } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { ATTENDANCE_STATUS_LABELS } from "@/lib/constants";
import { userFullName } from "@/lib/utils";

export function StaffAttendancePage() {
  const { data: attendance, isLoading } = useQuery({
    queryKey: ["attendance"],
    queryFn: () =>
      api
        .get<Paginated<Attendance>>("/staff/attendance/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  const queryClient = useQueryClient();

  return (
    <div className="space-y-6">
      <PageHeader title="Staff attendance" description="Record and review daily attendance.">
        <RecordAttendanceDialog onDone={() => queryClient.invalidateQueries({ queryKey: ["attendance"] })} />
      </PageHeader>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (attendance?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No attendance records.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(attendance?.results ?? []).map((a) => (
            <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-medium">
                  {a.staff_name}{" "}
                  <span className="text-muted-foreground text-xs">({a.employee_id})</span>
                </p>
                <p className="text-muted-foreground text-xs">
                  {a.date} · in {a.check_in ?? "-"} · out {a.check_out ?? "-"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={[
                    a.status === "present" && "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
                    a.status === "late" && "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
                    a.status === "absent" && "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
                    a.status === "leave" && "bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300",
                  ]
                    .filter(Boolean)
                    .join(" rounded-full px-2.5 py-0.5 text-xs font-medium")}
                >
                  {ATTENDANCE_STATUS_LABELS[a.status] ?? a.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RecordAttendanceDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [staff, setStaff] = useState<string>("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [status, setStatus] = useState("present");
  const [notes, setNotes] = useState("");

  const { data: staffList } = useQuery({
    queryKey: ["staff", "options"],
    queryFn: () =>
      api.get<Paginated<Staff>>("/staff/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/staff/attendance/", {
        staff: Number(staff),
        date,
        check_in: checkIn || null,
        check_out: checkOut || null,
        status,
        notes,
      }),
    onSuccess: () => {
      success("Attendance recorded");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to record attendance.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Record attendance
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Record attendance</DialogTitle>
          <DialogDescription>
            <CalendarCheck className="inline size-4" /> {date}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Staff member</Label>
            <Select value={staff} onValueChange={setStaff}>
              <SelectTrigger><SelectValue placeholder="Select staff" /></SelectTrigger>
              <SelectContent>
                {(staffList?.results ?? []).map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {userFullName(s.user_details)} ({s.employee_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label>Date</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Check in</Label>
              <Input type="time" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Check out</Label>
              <Input type="time" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="present">Present</SelectItem>
                  <SelectItem value="absent">Absent</SelectItem>
                  <SelectItem value="late">Late</SelectItem>
                  <SelectItem value="leave">On leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!staff || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Clock /> Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
