import { NavLink } from "react-router-dom";
import { ChevronRight, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { getNavGroups } from "@/config/navigation";

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { can, canAny, user } = useAuth();
  const groups = getNavGroups(can, canAny, user?.role_code);

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-2.5 border-b px-5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Activity className="size-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold">Mimosa Hospital</p>
          <p className="text-muted-foreground text-xs">Hospital Management</p>
        </div>
      </div>
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="text-muted-foreground mb-1.5 px-3 text-xs font-medium tracking-wider uppercase">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        cn(
                          "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                          isActive
                            ? "bg-primary/10 text-primary"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <Icon className="size-4 shrink-0" />
                          <span className="flex-1">{item.label}</span>
                          <ChevronRight
                            className={cn(
                              "size-3.5 transition-transform",
                              isActive ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-50"
                            )}
                          />
                        </>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </div>
  );
}
