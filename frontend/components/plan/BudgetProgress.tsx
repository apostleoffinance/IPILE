import { MoneyAmount } from "@/components/financial/MoneyAmount";

const statusClass: Record<string, string> = {
  healthy: "bg-healthy",
  warning: "bg-warning",
  critical: "bg-critical",
};

const statusText: Record<string, string> = {
  healthy: "text-muted",
  warning: "text-warning",
  critical: "text-critical",
};

export function BudgetProgress({
  categoryName,
  allocated,
  spent,
  remaining,
  utilization,
  status,
}: {
  categoryName: string;
  allocated: string;
  spent: string;
  remaining: string;
  utilization: string | null;
  status: string;
}) {
  const ratio = utilization == null ? 1 : Number(utilization);
  const width = Math.min(100, Math.max(0, Number.isFinite(ratio) ? ratio * 100 : 100));
  const usedLabel =
    utilization == null ? "unallocated spend" : `${Math.round(Number(utilization) * 100)}% used`;

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm">{categoryName}</p>
        <p className="text-xs text-muted">
          <MoneyAmount amount={spent} /> of <MoneyAmount amount={allocated} />
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-subtle">
        <div className={`h-full ${statusClass[status] ?? "bg-healthy"}`} style={{ width: `${width}%` }} />
      </div>
      <p className={`text-xs ${statusText[status] ?? "text-muted"}`}>
        Remaining <MoneyAmount amount={remaining} /> · {usedLabel}
      </p>
    </div>
  );
}
