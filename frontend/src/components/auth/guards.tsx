import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Loader2 className="size-8 animate-spin text-primary" />
          <p className="text-sm">Loading…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}

export function RoleRoute({
  children,
  permission,
  anyPermission,
}: {
  children: ReactNode;
  permission?: string;
  anyPermission?: string[];
}) {
  const { can, canAny, user } = useAuth();

  if (permission && !can(permission)) {
    return <Navigate to="/403" replace />;
  }
  if (anyPermission && !canAny(anyPermission)) {
    return <Navigate to="/403" replace />;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function GuestRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();

  if (isAuthenticated && user) {
    return <Navigate to={user.dashboard_path} replace />;
  }
  return <>{children}</>;
}
