import { useState } from "react";
import { BedDouble, Building2, Loader2, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Bed, Department, Paginated, Room, Ward } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { BED_STATUS_LABELS, BED_STATUS_VARIANTS, WARD_TYPE_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";

interface WardBoard {
  ward: { id: number; name: string; type: string; capacity: number | null };
  beds: Bed[];
  rooms: { id: number; room_number: string; room_type: string; capacity: number | null; beds: Bed[] }[];
}

const BED_DOT: Record<string, string> = {
  available: "bg-emerald-500",
  occupied: "bg-rose-500",
  reserved: "bg-amber-500",
  maintenance: "bg-slate-400",
  cleaning: "bg-sky-500",
  out_of_service: "bg-slate-700",
};

export function BedsPage() {
  const { can } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Bed | null>(null);
  const [newStatus, setNewStatus] = useState<string>("available");
  const [newBedType, setNewBedType] = useState("standard");
  const [wardFilter, setWardFilter] = useState("");
  const [roomFilter, setRoomFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [bedTypeFilter, setBedTypeFilter] = useState("");
  const [patientSearch, setPatientSearch] = useState("");

  const { data: board, isLoading } = useQuery({
    queryKey: ["beds", "board"],
    queryFn: () =>
      api.get<WardBoard[]>("/admissions/beds/board/").then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: async () => {
      if (newStatus !== selected!.status) {
        await api.post(`/admissions/beds/${selected!.id}/set_status/`, { status: newStatus });
      }
      if (newBedType !== selected!.bed_type) {
        await api.patch(`/admissions/beds/${selected!.id}/`, { bed_type: newBedType });
      }
    },
    onSuccess: () => {
      success("Bed updated");
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["beds"] });
      queryClient.invalidateQueries({ queryKey: ["admissions"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update bed.")),
  });

  const allBeds = (board ?? []).flatMap((ward) => ward.beds);
  const counts = allBeds.reduce(
    (acc, w) => {
      acc[w.status] = (acc[w.status] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );
  const visibleWards = (board ?? []).filter((w) => !wardFilter || String(w.ward.id) === wardFilter);

  return (
    <div className="space-y-6">
      <PageHeader title="Bed management" description="Live bed board grouped by ward.">
        <div className="flex flex-wrap gap-3">
          {Object.entries(BED_STATUS_LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={cn("size-2.5 rounded-full", BED_DOT[key])} />
              {label} {counts[key] ?? 0}
            </div>
          ))}
        </div>
      </PageHeader>

      {(can("admissions.update") || can("inpatient.manage_beds")) && <FacilitySetup />}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Input placeholder="Search patient or bed" value={patientSearch} onChange={(e) => setPatientSearch(e.target.value)} />
        <select className="border-input h-9 rounded-md border bg-transparent px-3 text-sm" value={wardFilter} onChange={(e) => { setWardFilter(e.target.value); setRoomFilter(""); }}>
          <option value="">All wards</option>{(board ?? []).map((w) => <option key={w.ward.id} value={w.ward.id}>{w.ward.name}</option>)}
        </select>
        <select className="border-input h-9 rounded-md border bg-transparent px-3 text-sm" value={roomFilter} onChange={(e) => setRoomFilter(e.target.value)}>
          <option value="">All rooms</option>{visibleWards.flatMap((w) => w.rooms.map((r) => <option key={r.id} value={r.id}>{w.ward.name} · {r.room_number}</option>))}
        </select>
        <select className="border-input h-9 rounded-md border bg-transparent px-3 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All bed statuses</option>{Object.entries(BED_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select className="border-input h-9 rounded-md border bg-transparent px-3 text-sm" value={bedTypeFilter} onChange={(e) => setBedTypeFilter(e.target.value)}>
          <option value="">All bed types</option>{["standard", "private", "icu", "maternity", "pediatric", "isolation"].map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
      </div>

      {isLoading ? (
        <Skeleton className="h-60" />
      ) : (board ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No wards configured.</p>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {visibleWards.map((ward) => {
            const rooms = ward.rooms.filter((r) => !roomFilter || String(r.id) === roomFilter).map((room) => ({
              ...room,
              beds: room.beds.filter((b) => (!statusFilter || b.status === statusFilter)
                && (!bedTypeFilter || b.bed_type === bedTypeFilter)
                && (!patientSearch || `${b.bed_number} ${b.current_patient?.full_name ?? ""} ${b.current_patient?.patient_number ?? ""}`.toLowerCase().includes(patientSearch.toLowerCase()))),
            })).filter((room) => room.beds.length > 0 || (!statusFilter && !bedTypeFilter && !patientSearch));
            const wardBeds = rooms.flatMap((r) => r.beds);
            if (wardBeds.length === 0) return null;
            return (
            <Card key={ward.ward.id}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <BedDouble className="size-4 text-primary" />
                  {ward.ward.name}
                </CardTitle>
                <CardDescription>
                  {WARD_TYPE_LABELS[ward.ward.type] ?? ward.ward.type} ·{" "}
                  {wardBeds.filter((b) => b.status === "available").length} of {wardBeds.length} available
                  {ward.ward.capacity != null ? ` · capacity ${ward.ward.capacity}` : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {rooms.map((room) => (
                    <section key={room.id} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <h3 className="font-medium">Room {room.room_number} <span className="text-muted-foreground">· {room.room_type}</span></h3>
                        <span className="text-muted-foreground text-xs">
                          {room.beds.filter((b) => b.status === "available").length}/{room.beds.length} available
                          {room.capacity != null ? ` · capacity ${room.capacity}` : ""}
                        </span>
                      </div>
                      <div className="grid grid-cols-4 gap-2">
                        {room.beds.map((bed) => (
                    <button
                      key={bed.id}
                      onClick={() => { setSelected(bed); setNewStatus(bed.status); setNewBedType(bed.bed_type); }}
                      title={`${bed.bed_number} — ${BED_STATUS_LABELS[bed.status]}`}
                      className={cn(
                        "flex aspect-square flex-col items-center justify-center rounded-lg border text-xs font-medium transition-colors hover:opacity-80",
                        BED_STATUS_VARIANTS[bed.status] === "success" && "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
                        BED_STATUS_VARIANTS[bed.status] === "destructive" && "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300",
                        BED_STATUS_VARIANTS[bed.status] === "warning" && "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
                        BED_STATUS_VARIANTS[bed.status] === "neutral" && "border-slate-300 bg-slate-50 text-slate-500 dark:border-slate-500/30 dark:bg-slate-500/15 dark:text-slate-300"
                      )}
                    >
                      <span>{bed.bed_number}</span>
                      <span className="text-[9px] font-normal">{bed.bed_type}</span>
                      {bed.current_patient && (
                        <span className="max-w-full truncate px-1 text-[10px] font-normal">
                          {bed.current_patient.full_name}
                        </span>
                      )}
                    </button>
                  ))}
                      </div>
                    </section>
                  ))}
                  {rooms.length === 0 && <p className="text-muted-foreground text-sm">No matching beds in this ward.</p>}
                </div>
              </CardContent>
            </Card>
            );
          })}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              Bed {selected?.bed_number} — {selected?.room_name}
            </DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(BED_STATUS_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setNewStatus(key)}
                className={cn(
                  "rounded-lg border p-3 text-sm font-medium transition-colors",
                  newStatus === key
                    ? "border-primary bg-primary/5 text-primary"
                    : "hover:bg-muted/50"
                )}
              >
                <span className={cn("mb-1.5 block size-2.5 rounded-full", BED_DOT[key])} />
                {label}
              </button>
            ))}
          </div>
          <Label>Bed type</Label>
          <select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={newBedType} onChange={(e) => setNewBedType(e.target.value)}>
            {["standard", "private", "icu", "maternity", "pediatric", "isolation"].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          {selected?.current_patient && (
            <p className="text-muted-foreground text-sm">Assigned to {selected.current_patient.full_name}</p>
          )}
          <DialogFooter>
            <Button
              onClick={() => mutation.mutate()}
              disabled={!selected || (newStatus === selected.status && newBedType === selected.bed_type) || mutation.isPending}
            >
              {mutation.isPending && <Loader2 className="animate-spin" />}
              Save status
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function FacilitySetup() {
  const { can } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const canManageWards = can("admissions.update");
  const canManageBeds = can("inpatient.manage_beds");
  const [wardName, setWardName] = useState("");
  const [wardId, setWardId] = useState("");
  const [wardCode, setWardCode] = useState("");
  const [wardType, setWardType] = useState("general");
  const [wardCapacity, setWardCapacity] = useState("");
  const [wardDepartment, setWardDepartment] = useState("");
  const [roomWard, setRoomWard] = useState("");
  const [roomId, setRoomId] = useState("");
  const [roomNumber, setRoomNumber] = useState("");
  const [roomType, setRoomType] = useState("general");
  const [roomCapacity, setRoomCapacity] = useState("");
  const [bedRoom, setBedRoom] = useState("");
  const [bedNumber, setBedNumber] = useState("");
  const [bedType, setBedType] = useState("standard");
  const { data: wardsData } = useQuery({
    queryKey: ["inpatient", "wards"],
    queryFn: () => api.get<Paginated<Ward>>("/admissions/wards/", { params: { page_size: 200 } }).then((r) => r.data),
  });
  const { data: roomsData } = useQuery({
    queryKey: ["inpatient", "rooms"],
    queryFn: () => api.get<Paginated<Room>>("/admissions/rooms/", { params: { page_size: 200 } }).then((r) => r.data),
  });
  const departments = useQuery({
    queryKey: ["departments", "inpatient-facilities"],
    queryFn: () => api.get<Paginated<Department>>("/departments/", { params: { page_size: 200 } }).then((r) => r.data.results),
    enabled: canManageWards,
  });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["inpatient"] });
    queryClient.invalidateQueries({ queryKey: ["beds"] });
  };
  const createWard = useMutation({
    mutationFn: () => {
      const values = {
        name: wardName,
        code: wardCode,
        ward_type: wardType,
        capacity: wardCapacity ? Number(wardCapacity) : null,
        department: wardDepartment ? Number(wardDepartment) : null,
      };
      return wardId
        ? api.patch(`/admissions/wards/${wardId}/`, values)
        : api.post("/admissions/wards/", values);
    },
    onSuccess: () => { success(wardId ? "Ward updated" : "Ward created"); setWardId(""); setWardName(""); setWardCode(""); refresh(); },
    onError: (e) => error(getErrorMessage(e, "Unable to create ward.")),
  });
  const toggleWard = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      api.patch(`/admissions/wards/${id}/`, { is_active }),
    onSuccess: () => { success("Ward status updated"); refresh(); },
    onError: (e) => error(getErrorMessage(e, "Unable to update ward.")),
  });
  const createRoom = useMutation({
    mutationFn: () => {
      const values = {
      ward: Number(roomWard), room_number: roomNumber, room_type: roomType,
      capacity: roomCapacity ? Number(roomCapacity) : null,
      };
      return roomId
        ? api.patch(`/admissions/rooms/${roomId}/`, values)
        : api.post("/admissions/rooms/", values);
    },
    onSuccess: () => { success(roomId ? "Room updated" : "Room created"); setRoomId(""); setRoomNumber(""); refresh(); },
    onError: (e) => error(getErrorMessage(e, "Unable to create room.")),
  });
  const createBed = useMutation({
    mutationFn: () => api.post("/admissions/beds/", {
      room: Number(bedRoom), bed_number: bedNumber, bed_type: bedType,
    }),
    onSuccess: () => { success("Bed registered"); setBedNumber(""); refresh(); },
    onError: (e) => error(getErrorMessage(e, "Unable to register bed.")),
  });
  const activeWards = (wardsData?.results ?? []).filter((w) => w.is_active);
  const activeRooms = (roomsData?.results ?? []).filter((r) => activeWards.some((w) => w.id === r.ward));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><Building2 className="size-4" /> Facility setup</CardTitle>
        <CardDescription>Register wards, rooms and beds. Capacity limits are enforced when beds are added.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-3">
        {canManageWards && <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); createWard.mutate(); }}>
          <h3 className="font-medium">{wardId ? "Edit ward" : "New ward"}</h3>
          <Label>Existing ward (optional)</Label><select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={wardId} onChange={(e) => {
            const selectedWard = (wardsData?.results ?? []).find((w) => String(w.id) === e.target.value);
            setWardId(e.target.value);
            if (selectedWard) {
              setWardName(selectedWard.name); setWardCode(selectedWard.code); setWardType(selectedWard.ward_type);
              setWardCapacity(selectedWard.capacity == null ? "" : String(selectedWard.capacity));
              setWardDepartment(selectedWard.department == null ? "" : String(selectedWard.department));
            }
          }}>
            <option value="">Create a new ward</option>{(wardsData?.results ?? []).map((w) => <option key={w.id} value={w.id}>{w.name}{w.is_active ? "" : " (inactive)"}</option>)}
          </select>
          <Label>Ward name</Label><Input required value={wardName} onChange={(e) => setWardName(e.target.value)} />
          <Label>Code</Label><Input value={wardCode} onChange={(e) => setWardCode(e.target.value)} />
          <Label>Ward type</Label><select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={wardType} onChange={(e) => setWardType(e.target.value)}>
            {Object.entries(WARD_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <Label>Capacity (optional)</Label><Input type="number" min="1" value={wardCapacity} onChange={(e) => setWardCapacity(e.target.value)} />
          <Label>Department (optional)</Label><select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={wardDepartment} onChange={(e) => setWardDepartment(e.target.value)}>
            <option value="">Select a department</option>{(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <Button type="submit" disabled={!wardName.trim() || createWard.isPending}><Plus /> {wardId ? "Save ward" : "Create ward"}</Button>
          <div className="space-y-1 border-t pt-3">
            {activeWards.map((w) => <div key={w.id} className="flex items-center justify-between gap-2 text-sm">
              <span>{w.name}</span>
              <Button type="button" size="sm" variant="outline" disabled={toggleWard.isPending} onClick={() => toggleWard.mutate({ id: w.id, is_active: false })}>Deactivate</Button>
            </div>)}
            {(wardsData?.results ?? []).filter((w) => !w.is_active).map((w) => <div key={w.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">{w.name} (inactive)</span>
              <Button type="button" size="sm" variant="outline" disabled={toggleWard.isPending} onClick={() => toggleWard.mutate({ id: w.id, is_active: true })}>Activate</Button>
            </div>)}
          </div>
        </form>}
        {canManageWards && <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); createRoom.mutate(); }}>
          <h3 className="font-medium">{roomId ? "Edit room" : "New room"}</h3>
          <Label>Existing room (optional)</Label><select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={roomId} onChange={(e) => {
            const selectedRoom = (roomsData?.results ?? []).find((r) => String(r.id) === e.target.value);
            setRoomId(e.target.value);
            if (selectedRoom) { setRoomWard(String(selectedRoom.ward)); setRoomNumber(selectedRoom.room_number); setRoomType(selectedRoom.room_type); setRoomCapacity(selectedRoom.capacity == null ? "" : String(selectedRoom.capacity)); }
          }}>
            <option value="">Create a new room</option>{(roomsData?.results ?? []).map((r) => <option key={r.id} value={r.id}>{r.ward_name} · {r.room_number}</option>)}
          </select>
          <Label>Ward</Label><select required className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={roomWard} onChange={(e) => setRoomWard(e.target.value)}>
            <option value="">Select ward</option>{activeWards.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </select>
          <Label>Room number</Label><Input required value={roomNumber} onChange={(e) => setRoomNumber(e.target.value)} />
          <Label>Room type</Label><Input required value={roomType} onChange={(e) => setRoomType(e.target.value)} />
          <Label>Capacity (optional)</Label><Input type="number" min="1" value={roomCapacity} onChange={(e) => setRoomCapacity(e.target.value)} />
          <Button type="submit" disabled={!roomWard || !roomNumber.trim() || createRoom.isPending}><Plus /> {roomId ? "Save room" : "Create room"}</Button>
        </form>}
        {canManageBeds && <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); createBed.mutate(); }}>
          <h3 className="font-medium">Register bed</h3>
          <Label>Room</Label><select required className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={bedRoom} onChange={(e) => setBedRoom(e.target.value)}>
            <option value="">Select room</option>{activeRooms.map((r) => <option key={r.id} value={r.id}>{r.ward_name} · {r.room_number}</option>)}
          </select>
          <Label>Bed number</Label><Input required value={bedNumber} onChange={(e) => setBedNumber(e.target.value)} />
          <Label>Bed type</Label><select className="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm" value={bedType} onChange={(e) => setBedType(e.target.value)}>
            {["standard", "private", "icu", "maternity", "pediatric", "isolation"].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          <Button type="submit" disabled={!bedRoom || !bedNumber.trim() || createBed.isPending}><Plus /> Register bed</Button>
        </form>}
      </CardContent>
    </Card>
  );
}
