import { Link } from "react-router-dom";
import { AlertOctagon, Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ForbiddenPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300">
        <AlertOctagon className="size-8" />
      </div>
      <h1 className="text-3xl font-semibold">403 — Access denied</h1>
      <p className="text-muted-foreground max-w-md text-sm">
        You do not have permission to view this page. If you believe this is a mistake, contact
        your system administrator.
      </p>
      <div className="flex gap-3">
        <Link to="/dashboard">
          <Button>Back to dashboard</Button>
        </Link>
        <Link to="/login">
          <Button variant="outline">Sign in</Button>
        </Link>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-500/15 dark:text-slate-300">
        <Compass className="size-8" />
      </div>
      <h1 className="text-3xl font-semibold">404 — Page not found</h1>
      <p className="text-muted-foreground max-w-md text-sm">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link to="/dashboard">
        <Button>Back to dashboard</Button>
      </Link>
    </div>
  );
}
