import { useState } from "react";
import { Loader2, UserPlus, Users } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Paginated, Staff } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
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
import { STAFF_STATUS_LABELS, STAFF_STATUS_VARIANTS } from "@/lib/constants";
import { userFullName } from "@/lib/utils";

export function StaffPage() {
  const [search, setSearch] = useState("");

  const { data: staff, isLoading } = useQuery({
    queryKey: ["staff", search],
    queryFn: () =>
      api
        .get<Paginated<Staff>>("/staff/", { params: { search: search || undefined, page_size: 100 } })
        .then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Staff" description="Manage employees and their accounts.">
        <NewStaffDialog />
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={Users} title="Total staff" value={staff?.count ?? 0} />
        <StatCard
          icon={Users}
          title="Active"
          value={(staff?.results ?? []).filter((s) => s.employment_status === "active").length}
        />
        <StatCard
          icon={Users}
          title="On leave"
          value={(staff?.results ?? []).filter((s) => s.employment_status === "on_leave").length}
        />
      </div>

      <div className="space-y-3">
        <Input
          placeholder="Search by name, employee ID or job title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        {isLoading ? (
          <Skeleton className="h-40" />
        ) : (staff?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-10 text-center text-sm">No staff found.</p>
        ) : (
          <div className="divide-y rounded-lg border">
            {(staff?.results ?? []).map((s) => (
              <div key={s.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium">
                    {userFullName(s.user_details)}{" "}
                    <span className="text-muted-foreground text-xs">({s.employee_id})</span>
                  </p>
                  <p className="text-muted-foreground text-xs">
                    {s.job_title || "-"} · {s.department || "-"} · joined {s.date_joined}
                  </p>
                </div>
                <div className="text-right">
                  <StatusBadge
                    value={s.employment_status}
                    labels={STAFF_STATUS_LABELS}
                    variants={STAFF_STATUS_VARIANTS}
                  />
                  <p className="text-muted-foreground mt-0.5 text-xs">{s.user_details?.email}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function NewStaffDialog() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [department, setDepartment] = useState("");
  const [password, setPassword] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [qualifications, setQualifications] = useState("");
  const [dateJoined, setDateJoined] = useState("");
  const [salary, setSalary] = useState("");
  const [address, setAddress] = useState("");

  const { data: roles } = useQuery({
    queryKey: ["auth", "roles"],
    queryFn: () => api.get<{ code: string; name: string }[]>("/users/roles/").then((r) => r.data),
  });
  const { data: departments } = useQuery({
    queryKey: ["departments", "options"],
    queryFn: () =>
      api.get<Paginated<{ id: number; name: string }>>("/departments/", { params: { page_size: 200 } }).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/staff/", {
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        phone,
        role,
        department: department ? Number(department) : null,
        password,
        employee_id: employeeId,
        job_title: jobTitle,
        license_number: licenseNumber,
        qualifications,
        date_joined: dateJoined,
        salary: salary ? Number(salary) : null,
        address,
      }),
    onSuccess: () => {
      success("Staff member added", "A user account was created.");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["staff"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to add staff member.")),
  });

  const ready = username && email && firstName && lastName && role && password && employeeId && dateJoined;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus /> Add staff
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add staff member</DialogTitle>
          <DialogDescription>Creates a user account plus staff profile.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>First name</Label>
            <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Last name</Label>
            <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Username</Label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Phone</Label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Password</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
              <SelectContent>
                {(roles ?? []).map((r) => (
                  <SelectItem key={r.code} value={r.code}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Department</Label>
            <Select value={department} onValueChange={setDepartment}>
              <SelectTrigger><SelectValue placeholder="Select department" /></SelectTrigger>
              <SelectContent>
                {(departments?.results ?? []).map((d) => (
                  <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Employee ID</Label>
            <Input value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Date joined</Label>
            <Input type="date" value={dateJoined} onChange={(e) => setDateJoined(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Job title</Label>
            <Input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>License number</Label>
            <Input value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Qualifications</Label>
            <Input value={qualifications} onChange={(e) => setQualifications(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Salary</Label>
            <Input type="number" min={0} step="0.01" value={salary} onChange={(e) => setSalary(e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Address</Label>
          <Input value={address} onChange={(e) => setAddress(e.target.value)} />
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!ready || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <UserPlus /> Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
