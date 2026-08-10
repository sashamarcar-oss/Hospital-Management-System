import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Activity } from "lucide-react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex size-10 items-center justify-center rounded-lg bg-white/15">
            <Activity className="size-6" />
          </div>
          <div>
            <p className="text-lg font-semibold">Mimosa Hospital</p>
            <p className="text-sm opacity-80">Hospital Management System</p>
          </div>
        </div>
        <div className="space-y-4">
          <h2 className="max-w-md text-3xl font-semibold leading-tight">
            Complete care, from registration to discharge — in one secure platform.
          </h2>
          <p className="max-w-md text-sm opacity-85">
            Manage patients, appointments, consultations, laboratory, pharmacy, billing and
            reporting with role-based access and full audit trails.
          </p>
        </div>
        <p className="text-xs opacity-70">
          © {new Date().getFullYear()} Mimosa Hospital. Authorized access only.
        </p>
      </div>
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Activity className="size-6" />
            </div>
            <div>
              <p className="font-semibold">Mimosa Hospital</p>
              <p className="text-muted-foreground text-xs">Hospital Management System</p>
            </div>
          </div>
          {children}
          <p className="text-muted-foreground mt-8 text-center text-xs">
            Need an account?{" "}
            <Link to="/register" className="text-primary font-medium hover:underline">
              Register as a patient
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
