import { MoneyAmount } from "@/components/financial/MoneyAmount";

export function GoalProgress({
  name,
  type,
  current,
  target,
  percent,
  deadline,
  requiredMonthly,
  status,
}: {
  name: string;
  type: string;
  current: string;
  target: string;
  percent: number;
  deadline: string | null;
  requiredMonthly: string;
  status: string;
}) {
  const width = Math.min(100, Math.max(0, percent));
  return (
    <div className="space-y-3 rounded-md border border-line bg-surface p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">{name}</h2>
          <p className="mt-1 text-sm capitalize text-muted">
            {type} · {percent}% · {status}
            {deadline ? ` · ${deadline}` : ""}
          </p>
        </div>
        <p className="text-sm text-muted">
          <MoneyAmount amount={current} /> of <MoneyAmount amount={target} />
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-subtle">
        <div
          className={`h-full ${status === "completed" ? "bg-healthy" : "bg-accent"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <p className="text-xs text-muted">
        Required monthly <MoneyAmount amount={requiredMonthly} />
      </p>
    </div>
  );
}
