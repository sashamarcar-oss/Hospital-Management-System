import { useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCheck, ChevronDown, LogOut, Menu, Moon, Sun, UserRound } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiPost } from "@/lib/api";
import type { Notification, Paginated } from "@/lib/types";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { initials } from "@/lib/utils";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { SidebarContent } from "@/components/layout/sidebar";

export function Topbar() {
  const { user, logout, hasRole } = useAuth();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light"
  );

  const { data: unreadCount } = useQuery({
    queryKey: ["notifications", "unread_count"],
    queryFn: () => api.get<{ count: number }>("/core/notifications/unread_count/").then((r) => r.data.count),
    refetchInterval: 30_000,
  });

  const { data: recentNotifications } = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () =>
      api
        .get<Paginated<Notification>>("/core/notifications/", { params: { page_size: 6 } })
        .then((r) => r.data.results),
    refetchInterval: 30_000,
  });

  const markAllRead = useMutation({
    mutationFn: () => apiPost("/core/notifications/mark_all_read/"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      success("Notifications marked as read");
    },
    onError: (err) => error("Failed to update notifications", String(err)),
  });

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
  };

  const handleLogout = async () => {
    await logout();
  };

  const firstName = user?.first_name ?? user?.username ?? "";
  const lastName = user?.last_name ?? "";

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur sm:px-6">
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden">
            <Menu />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-72 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <SidebarContent onNavigate={() => setSheetOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="hidden text-sm sm:block">
        <p className="font-medium">{user?.role_name}</p>
        <p className="text-muted-foreground text-xs capitalize">{user?.username}</p>
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "light" ? <Moon /> : <Sun />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
              <Bell />
              {typeof unreadCount === "number" && unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-semibold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="flex items-center justify-between px-2 py-1.5">
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => markAllRead.mutate()}
                disabled={!unreadCount}
              >
                <CheckCheck /> Mark all read
              </Button>
            </div>
            <DropdownMenuSeparator />
            <div className="max-h-80 overflow-y-auto">
              {recentNotifications?.length ? (
                recentNotifications.slice(0, 6).map((n) => (
                  <Link key={n.id} to={n.link || "/notifications"}>
                    <DropdownMenuItem className="items-start gap-2 py-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-sm font-medium">{n.title}</p>
                          {!n.is_read && <span className="size-2 shrink-0 rounded-full bg-primary" />}
                        </div>
                        <p className="text-muted-foreground line-clamp-2 text-xs">{n.message}</p>
                      </div>
                    </DropdownMenuItem>
                  </Link>
                ))
              ) : (
                <p className="text-muted-foreground px-2 py-6 text-center text-sm">No notifications</p>
              )}
            </div>
            <DropdownMenuSeparator />
            <Link to="/notifications">
              <DropdownMenuItem>View all notifications</DropdownMenuItem>
            </Link>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-full p-1 hover:bg-accent">
              <Avatar className="size-8">
                {user?.profile_photo ? (
                  <AvatarImage src={user.profile_photo} alt={firstName} />
                ) : null}
                <AvatarFallback className="bg-primary/10 text-primary text-xs">
                  {initials(firstName, lastName)}
                </AvatarFallback>
              </Avatar>
              <ChevronDown className="text-muted-foreground hidden size-4 sm:block" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="truncate text-sm font-medium">{firstName} {lastName}</p>
              <p className="text-muted-foreground text-xs">{user?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <Link to="/change-password">
              <DropdownMenuItem>
                <UserRound /> Change password
              </DropdownMenuItem>
            </Link>
            {hasRole("patient") && (
              <Link to="/portal">
                <DropdownMenuItem>My Patient Portal</DropdownMenuItem>
              </Link>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={handleLogout}>
              <LogOut /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
