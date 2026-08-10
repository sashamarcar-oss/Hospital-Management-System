import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Topbar } from "@/components/layout/topbar";
import { SidebarContent } from "@/components/layout/sidebar";
import { useAuth } from "@/hooks/use-auth";

const PATIENT_PATHS = ["/portal", "/change-password"];

export function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();

  if (user?.role_code === "patient") {
    if (!PATIENT_PATHS.includes(location.pathname)) {
      return <Navigate to="/portal" replace />;
    }
    return (
      <div className="flex min-h-screen flex-col">
        <Topbar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-5xl">
            <Outlet />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="bg-sidebar sticky top-0 hidden h-screen w-64 shrink-0 border-r lg:block">
        <SidebarContent />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
