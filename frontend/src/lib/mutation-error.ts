import { toast } from "sonner";
import { getErrorMessage, getFieldErrors } from "@/lib/api";

export function handleMutationError(
  error: unknown,
  fallback: string,
  setFormErrors?: (errors: Record<string, string>) => void
) {
  if (setFormErrors) {
    const fieldErrors = getFieldErrors(error);
    if (Object.keys(fieldErrors).length > 0) {
      setFormErrors(fieldErrors);
    }
  }
  toast.error(getErrorMessage(error, fallback));
}
