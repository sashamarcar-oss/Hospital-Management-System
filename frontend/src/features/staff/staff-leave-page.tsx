import { useState } from "react";
import { CalendarOff, Check, Loader2, Plus, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { LeaveRequest, Paginated, Staff } from "@/lib/types";
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
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  LEAVE_STATUS_LABELS,
  LEAVE_TYPE_LABELS,
} from "@/lib/constants";
import { userFullName } from "@/lib/utils";

export function StaffLeavePage() {
  const queryClient = useQueryClient();
  const { data: leaves, isLoading } = useQuery({
    queryKey: ["leaves"],
    queryFn: () =>
      api
        .get<Paginated<LeaveRequest>>("/staff/leaves/", { params: { page_size: 100 } })
        .then((r) => r.data),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["leaves"] });
    queryClient.invalidateQueries({ queryKey: ["staff"] });
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Leave requests" description="Approve or reject staff leave.">
        <NewLeaveDialog onDone={invalidate} />
      </PageHeader>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (leaves?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No leave requests.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(leaves?.results ?? []).map((l) => (
            <LeaveRow key={l.id} leave={l} onDone={invalidate} />
          ))}
        </div>
      )}
    </div>
  );
}

function LeaveRow({ leave, onDone }: { leave: LeaveRequest; onDone: () => void }) {
  const { success, error } = useToast();
  const mutation = useMutation({
    mutationFn: (action: "approve" | "reject") =>
      api.post(`/staff/leaves/${leave.id}/${action}/`),
    onSuccess: () => {
      success("Leave updated");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Action failed.")),
  });

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0">
        <p className="font-medium">
          {leave.staff_name} · {LEAVE_TYPE_LABELS[leave.leave_type] ?? leave.leave_type}
        </p>
        <p className="text-muted-foreground text-xs">
          {leave.start_date} → {leave.end_date}
        </p>
        {leave.reason && <p className="text-muted-foreground text-xs italic">{leave.reason}</p>}
      </div>
      <div className="flex items-center gap-2">
        <span
          className={[
            leave.status === "approved" && "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
            leave.status === "rejected" && "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
            leave.status === "pending" && "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
          ]
            .filter(Boolean)
            .join(" rounded-full px-2.5 py-0.5 text-xs font-medium")}
        >
          {LEAVE_STATUS_LABELS[leave.status]}
        </span>
        {leave.status === "pending" && (
          <>
            <Button variant="outline" size="sm" onClick={() => mutation.mutate("approve")}>
              <Check /> Approve
            </Button>
            <Button variant="ghost" size="sm" onClick={() => mutation.mutate("reject")}>
              <X /> Reject
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function NewLeaveDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [staff, setStaff] = useState("");
  const [leaveType, setLeaveType] = useState("annual");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  const { data: staffList } = useQuery({
    queryKey: ["staff", "options"],
    queryFn: () =>
      api.get<Paginated<Staff>>("/staff/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/staff/leaves/", {
        staff: Number(staff),
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        reason,
      }),
    onSuccess: () => {
      success("Leave request created");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create leave request.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Plus /> Request leave
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New leave request</DialogTitle>
          <DialogDescription>
            <CalendarOff className="inline size-4" /> Submit a request for approval.
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
              <Label>Type</Label>
              <Select value={leaveType} onValueChange={setLeaveType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(LEAVE_TYPE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Start</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>End</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Reason</Label>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!(staff && startDate && endDate) || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <CalendarOff /> Submit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
