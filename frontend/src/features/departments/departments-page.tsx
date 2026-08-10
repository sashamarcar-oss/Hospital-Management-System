import { useState } from "react";
import { Building2, Loader2, Plus, Users } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "@/lib/api";
import type { Department, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";

export function DepartmentsPage() {
  const [search, setSearch] = useState("");
  const { data: departments, isLoading } = useQuery({
    queryKey: ["departments", search],
    queryFn: () =>
      api
        .get<Paginated<Department>>("/departments/", {
          params: { search: search || undefined, page_size: 100 },
        })
        .then((r) => r.data),
  });

  const queryClient = useQueryClient();

  return (
    <div className="space-y-6">
      <PageHeader title="Departments" description="Clinical and administrative departments.">
        <NewDepartmentDialog onDone={() => queryClient.invalidateQueries({ queryKey: ["departments"] })} />
      </PageHeader>

      <div className="space-y-3">
        <Input
          placeholder="Search departments..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        {isLoading ? (
          <Skeleton className="h-40" />
        ) : (departments?.results ?? []).length === 0 ? (
          <p className="text-muted-foreground py-10 text-center text-sm">No departments found.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(departments?.results ?? []).map((d) => (
              <Card key={d.id}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between gap-2">
                    <p className="flex items-center gap-2 font-medium">
                      <Building2 className="size-4 text-primary" /> {d.name}
                    </p>
                    {!d.is_active && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-500/15 dark:text-slate-300">
                        Inactive
                      </span>
                    )}
                  </div>
                  <p className="text-muted-foreground text-xs">{d.code}</p>
                  {d.description && (
                    <p className="text-muted-foreground mt-2 line-clamp-2 text-sm">{d.description}</p>
                  )}
                  <p className="mt-3 flex items-center gap-1 text-xs text-muted-foreground">
                    <Users className="size-3.5" /> {d.member_count} members
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function NewDepartmentDialog({ onDone }: { onDone: () => void }) {
  const { success, error } = useToast();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      api.post("/departments/", { name, code, description }),
    onSuccess: () => {
      success("Department created");
      onDone();
    },
    onError: (err) => error(getErrorMessage(err, "Unable to create department.")),
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>
          <Plus /> New department
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Create department</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Code</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            <Building2 /> Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
