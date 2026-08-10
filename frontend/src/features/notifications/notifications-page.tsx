import { Bell, CheckCheck, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "@/lib/api";
import type { Notification, Paginated } from "@/lib/types";
import { PageHeader } from "@/components/common/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { cn, formatDateTime } from "@/lib/utils";

export function NotificationsPage() {
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      api.get<Paginated<Notification>>("/core/notifications/").then((r) => r.data),
  });
  const notifications = data?.results;

  const markRead = useMutation({
    mutationFn: (id: number) => api.post(`/core/notifications/${id}/mark_read/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    onError: (err) => error(getErrorMessage(err, "Unable to update notification.")),
  });

  const markAllRead = useMutation({
    mutationFn: () => api.post("/core/notifications/mark_all_read/"),
    onSuccess: () => {
      success("All notifications marked as read");
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => error(getErrorMessage(err, "Unable to mark notifications read.")),
  });

  const unread = (notifications ?? []).filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6">
      <PageHeader title="Notifications" description="System alerts and activity.">
        <Button variant="outline" onClick={() => markAllRead.mutate()} disabled={unread === 0}>
          <CheckCheck /> Mark all read
        </Button>
      </PageHeader>

      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (notifications ?? []).length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">No notifications.</p>
      ) : (
        <div className="divide-y rounded-lg border">
          {(notifications ?? []).map((n) => (
            <div
              key={n.id}
              className={cn(
                "flex flex-wrap items-center justify-between gap-3 p-4",
                !n.is_read && "bg-primary/5"
              )}
            >
              <div className="min-w-0">
                <p className="flex items-center gap-2 font-medium">
                  {!n.is_read && <span className="size-2 rounded-full bg-primary" />}
                  {n.title}
                </p>
                <p className="text-muted-foreground text-sm">{n.message}</p>
                <p className="text-muted-foreground text-xs">{formatDateTime(n.created_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                {n.link && (
                  <Link to={n.link}>
                    <Button variant="outline" size="sm">View</Button>
                  </Link>
                )}
                {!n.is_read && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => markRead.mutate(n.id)}
                    disabled={markRead.isPending}
                  >
                    {markRead.isPending ? <Loader2 className="animate-spin" /> : <Bell />} Read
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
