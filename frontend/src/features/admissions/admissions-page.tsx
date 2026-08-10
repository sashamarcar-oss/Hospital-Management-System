import { useState } from "react";
import {
  ArrowRightLeft,
  BedDouble,
  Hospital,
  Loader2,
  Plus,
  UserPlus,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Admission, Paginated, Ward, Room, Bed, Department } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { PatientSelect } from "@/components/common/patient-select";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  ADMISSION_STATUS_LABELS,
  ADMISSION_STATUS_VARIANTS,
} from "@/lib/constants";
import { formatDateTime, userFullName } from "@/lib/utils";

function useOptions<T extends { id: number }>(url: string, params: Record<string, unknown> = {}) {
  const { data } = useQuery({
    queryKey: [url, params],
    queryFn: () =>
      api
        .get<Paginated<T>>(url, { params: { page_size: 200, ...params } })
        .then((r) => r.data.results),
    staleTime: 60_000,
  });
  return data ?? [];
}

export function AdmissionsPage() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("admitted");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const { data: admissions, isLoading } = useQuery({
    queryKey: ["admissions", status, search],
    queryFn: () =>
      api
        .get<Paginated<Admission>>("/admissions/", {
          params: { status, search: search || undefined, page_size: 100 },
        })
        .then((r) => r.data),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admissions"] });

  return (
    <div className="space-y-6">
      <PageHeader title="Admissions" description="Admitted, transferred and discharged inpatients.">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <UserPlus /> Admit patient
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Admit patient</DialogTitle>
              <DialogDescription>Assign a patient to a ward, room and bed.</DialogDescription>
            </DialogHeader>
            <AdmitForm onDone={() => { setOpen(false); invalidate(); }} />
          </DialogContent>
        </Dialog>
      </PageHeader>

      <Card>
        <CardContent className="pt-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admitted">Admitted</SelectItem>
                <SelectItem value="transferred">Transferred</SelectItem>
                <SelectItem value="discharged">Discharged</SelectItem>
                <SelectItem value="all">All</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Search patient..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-xs"
            />
          </div>

          {isLoading ? (
            <Skeleton className="h-40" />
          ) : (admissions?.results ?? []).length === 0 ? (
            <p className="text-muted-foreground py-10 text-center text-sm">No admissions found.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {(admissions?.results ?? []).map((a) => (
                <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="font-medium">{a.patient_details?.full_name}</p>
                    <p className="text-muted-foreground text-xs">
                      #{a.patient_details?.patient_number} · {a.department_name ?? "-"} ·{" "}
                      {a.ward_name ?? "-"} / {a.room_name ?? "-"} / {a.bed_name ?? "-"}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      Admitted {formatDateTime(a.admission_date)} · {userFullName(a.doctor_details) || "-"}
                    </p>
                    {a.diagnosis && (
                      <p className="text-muted-foreground text-xs italic">{a.diagnosis}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge
                      value={a.status}
                      labels={ADMISSION_STATUS_LABELS}
                      variants={ADMISSION_STATUS_VARIANTS}
                    />
                    {a.status === "admitted" && <TransferDialog admission={a} onDone={invalidate} />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AdmitForm({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [patient, setPatient] = useState<number | null>(null);
  const [doctor, setDoctor] = useState<string>("");
  const [department, setDepartment] = useState<string>("");
  const [ward, setWard] = useState<string>("");
  const [room, setRoom] = useState<string>("");
  const [bed, setBed] = useState<string>("");
  const [reason, setReason] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [notes, setNotes] = useState("");

  const staff = useOptions<{ id: number; name: string; user: number }>("/staff/");
  const departments = useOptions<Department>("/departments/");
  const wards = useOptions<Ward>("/admissions/wards/");
  const rooms = useOptions<Room>("/admissions/rooms/", ward ? { ward: Number(ward) } : {});
  const beds = useOptions<Bed>("/admissions/beds/", ward ? { room__ward: Number(ward) } : {});

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/admissions/", {
        patient,
        doctor: doctor ? Number(doctor) : null,
        department: department ? Number(department) : null,
        ward: ward ? Number(ward) : null,
        room: room ? Number(room) : null,
        bed: bed ? Number(bed) : null,
        admission_reason: reason,
        diagnosis,
        notes,
      }),
    onSuccess: () => {
      success("Patient admitted", "Bed marked as occupied.");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to admit patient.")),
  });

  const ready = patient && reason.trim();

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Patient</Label>
        <PatientSelect value={patient} onChange={setPatient} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Doctor</Label>
          <Select value={doctor} onValueChange={setDoctor}>
            <SelectTrigger><SelectValue placeholder="Select doctor" /></SelectTrigger>
            <SelectContent>
              {staff.map((s) => (
                <SelectItem key={s.id} value={String(s.user)}>{s.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Department</Label>
          <Select value={department} onValueChange={setDepartment}>
            <SelectTrigger><SelectValue placeholder="Select department" /></SelectTrigger>
            <SelectContent>
              {departments.map((d) => (
                <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Ward</Label>
          <Select value={ward} onValueChange={(v) => { setWard(v); setRoom(""); setBed(""); }}>
            <SelectTrigger><SelectValue placeholder="Select ward" /></SelectTrigger>
            <SelectContent>
              {wards.map((w) => (
                <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Room</Label>
          <Select value={room} onValueChange={setRoom}>
            <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
            <SelectContent>
              {rooms.map((r) => (
                <SelectItem key={r.id} value={String(r.id)}>{r.room_number}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Bed</Label>
          <Select value={bed} onValueChange={setBed}>
            <SelectTrigger><SelectValue placeholder="Select bed" /></SelectTrigger>
            <SelectContent>
              {beds.map((b) => (
                <SelectItem key={b.id} value={String(b.id)}>
                  {b.bed_number} ({b.status})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Reason for admission</Label>
          <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. severe pneumonia" />
        </div>
      </div>
      <div className="space-y-2">
        <Label>Admission diagnosis</Label>
        <Input value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label>Notes</Label>
        <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </div>
      <DialogFooter>
        <Button onClick={() => mutation.mutate()} disabled={!ready || mutation.isPending}>
          {mutation.isPending && <Loader2 className="animate-spin" />}
          <Plus /> Admit
        </Button>
      </DialogFooter>
    </div>
  );
}

function TransferDialog({ admission, onDone }: { admission: Admission; onDone: () => void }) {
  const { success, error } = useToast();
  const [open, setOpen] = useState(false);
  const [ward, setWard] = useState<string>("");
  const [room, setRoom] = useState<string>("");
  const [bed, setBed] = useState<string>("");

  const wards = useOptions<Ward>("/admissions/wards/");
  const rooms = useOptions<Room>("/admissions/rooms/", ward ? { ward: Number(ward) } : {});
  const beds = useOptions<Bed>("/admissions/beds/", ward ? { room__ward: Number(ward) } : {});

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/admissions/${admission.id}/transfer/`, {
        ward: Number(ward),
        room: Number(room),
        bed: Number(bed),
      }),
    onSuccess: () => {
      success("Patient transferred");
      setOpen(false);
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Transfer failed.")),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <ArrowRightLeft /> Transfer
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Transfer patient</DialogTitle>
          <DialogDescription>
            Move {admission.patient_details?.full_name} to a new ward, room and bed.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Ward</Label>
            <Select value={ward} onValueChange={(v) => { setWard(v); setRoom(""); setBed(""); }}>
              <SelectTrigger><SelectValue placeholder="Select ward" /></SelectTrigger>
              <SelectContent>
                {wards.map((w) => (
                  <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Room</Label>
            <Select value={room} onValueChange={setRoom}>
              <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
              <SelectContent>
                {rooms.map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>{r.room_number}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Bed</Label>
            <Select value={bed} onValueChange={setBed}>
              <SelectTrigger><SelectValue placeholder="Select bed" /></SelectTrigger>
              <SelectContent>
                {beds.map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.bed_number} ({b.status})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!(ward && room && bed) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <BedDouble /> Transfer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
