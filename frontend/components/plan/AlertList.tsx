import type { Alert } from "@/lib/api";

const severityClass: Record<string, string> = {
  warning: "text-warning",
  critical: "text-critical",
};

export function AlertList({
  alerts,
  onRead,
}: {
  alerts: Alert[];
  onRead: (id: string) => void;
}) {
  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div key={alert.id} className="flex items-start justify-between gap-4 rounded-md border border-line bg-surface p-4">
          <div>
            <p className={`text-xs uppercase tracking-wide ${severityClass[alert.severity] ?? "text-muted"}`}>
              {alert.severity}
            </p>
            <p className="mt-1 text-sm">{alert.title}</p>
            <p className="mt-1 text-sm text-muted">{alert.body}</p>
          </div>
          <button type="button" className="shrink-0 text-xs text-muted underline" onClick={() => onRead(alert.id)}>
            Mark read
          </button>
        </div>
      ))}
    </div>
  );
}
