import { FinancialAlert } from "@/components/financial/FinancialAlert";
import type { Alert } from "@/lib/api";

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
        <FinancialAlert key={alert.id} alert={alert} onRead={onRead} />
      ))}
    </div>
  );
}
