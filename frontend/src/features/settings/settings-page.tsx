import { useState } from "react";
import { Loader2, ShieldCheck, UserCog, UserPlus, Users } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Paginated } from "@/lib/types";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { formatDateTime } from "@/lib/utils";

interface UserRow {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: number | null;
  role_code: string;
  role_name: string;
  permission_codes: string[];
  department: number | null;
  is_active: boolean;
  is_patient_account: boolean;
  date_joined: string;
}

interface RoleRow {
  id: number;
  code: string;
  name: string;
  description: string;
  permission_codes: string[];
  dashboard_path: string;
}

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="User accounts and role permissions." />
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
        </TabsList>
        <TabsContent value="users">
          <UsersTab />
        </TabsContent>
        <TabsContent value="roles">
          <RolesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function UsersTab() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  const { data: users, isLoading } = useQuery({
    queryKey: ["users", search],
    queryFn: () =>
      api
        .get<Paginated<UserRow>>("/users/", { params: { search: search || undefined, page_size: 100 } })
        .then((r) => r.data),
  });

  const toggle = useMutation({
    mutationFn: (id: number) => api.post(`/users/${id}/toggle_active/`),
    onSuccess: () => {
      success("Account updated");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to update account.")),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Input
          placeholder="Search users..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <NewUserDialog onDone={() => queryClient.invalidateQueries({ queryKey: ["users"] })} />
      </div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (users?.results ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No users found.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(users?.results ?? []).map((u) => (
            <div key={u.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <p className="flex items-center gap-2 font-medium">
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username}
                  <span className="text-muted-foreground text-xs">@{u.username}</span>
                </p>
                <p className="text-muted-foreground text-xs">
                  {u.email} · {u.role_name} · joined {formatDateTime(u.date_joined)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={u.is_active
                    ? "rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
                    : "rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-500/15 dark:text-slate-300"}
                >
                  {u.is_active ? "Active" : "Disabled"}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggle.mutate(u.id)}
                  disabled={toggle.isPending}
                >
                  {toggle.isPending ? <Loader2 className="animate-spin" /> : <UserCog />}
                  {u.is_active ? "Disable" : "Enable"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewUserDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [password, setPassword] = useState("");

  const { data: roles } = useQuery({
    queryKey: ["roles", "options"],
    queryFn: () => api.get<RoleRow[]>("/users/roles/").then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/users/", {
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        phone,
        role: role ? Number(role) : null,
        password,
      }),
    onSuccess: () => {
      success("User created");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create user.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>
          <UserPlus /> New user
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create user account</DialogTitle>
          <DialogDescription>Assign a role to grant permissions.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Username</Label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Email</Label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>First name</Label>
            <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Last name</Label>
            <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Phone</Label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Password</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Role</Label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
            <SelectContent>
              {(roles ?? []).map((r) => (
                <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!(username && email && role && password) || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <UserPlus /> Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RolesTab() {
  const { data: roles, isLoading } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.get<RoleRow[]>("/users/roles/").then((r) => r.data),
  });

  return (
    <div>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (roles ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No roles configured.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(roles ?? []).map((r) => (
            <div key={r.id} className="rounded-lg border p-4">
              <p className="flex items-center gap-2 font-medium">
                <ShieldCheck className="size-4 text-primary" /> {r.name}
              </p>
              <p className="text-muted-foreground text-xs">{r.code}</p>
              {r.description && <p className="text-muted-foreground mt-1 text-sm">{r.description}</p>}
              <p className="mt-2 text-xs">
                <span className="font-medium">{r.permission_codes.length}</span>{" "}
                <span className="text-muted-foreground">permissions</span>
              </p>
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-muted-foreground">
                  View permissions
                </summary>
                <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs">
                  {r.permission_codes.map((p) => (
                    <li key={p} className="flex items-center gap-1">
                      <Users className="size-3 text-muted-foreground" /> {p}
                    </li>
                  ))}
                </ul>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
