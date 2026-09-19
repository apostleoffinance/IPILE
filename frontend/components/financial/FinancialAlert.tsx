import { AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Alert } from "@/lib/api";
import { cn } from "@/lib/utils";

export function FinancialAlert({
  alert,
  onRead,
  className,
}: {
  alert: Alert;
  onRead?: (id: string) => void;
  className?: string;
}) {
  const critical = alert.severity === "critical";
  const Icon = critical || alert.severity === "warning" ? AlertTriangle : Info;
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 border bg-surface px-4 py-3",
        critical ? "border-critical/40" : alert.severity === "warning" ? "border-warning/40" : "border-line",
        className,
      )}
    >
      <div className="flex gap-3">
        <Icon
          className={cn(
            "mt-0.5 h-4 w-4 shrink-0",
            critical ? "text-critical" : alert.severity === "warning" ? "text-warning" : "text-muted",
          )}
          aria-hidden
        />
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">{alert.severity}</p>
          <p className="mt-1 text-sm font-medium text-ink">{alert.title}</p>
          <p className="mt-1 text-sm text-muted">{alert.body}</p>
        </div>
      </div>
      {onRead ? (
        <Button type="button" variant="ghost" size="sm" onClick={() => onRead(alert.id)}>
          Mark read
        </Button>
      ) : null}
    </div>
  );
}
