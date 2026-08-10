import { Badge, badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

export function StatusBadge({
  value,
  labels,
  variants,
  fallback = "neutral",
}: {
  value: string;
  labels?: Record<string, string>;
  variants?: Record<string, BadgeVariant>;
  fallback?: BadgeVariant;
}) {
  return (
    <Badge variant={variants?.[value] ?? fallback}>
      {labels?.[value] ?? value.replace(/[_-]/g, " ")}
    </Badge>
  );
}
