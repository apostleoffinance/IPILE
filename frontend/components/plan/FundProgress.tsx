import { MoneyAmount } from "@/components/financial/MoneyAmount";

export function FundProgress({
  name,
  current,
  target,
  progress,
  coverageLabel,
  requiredMonthly,
  onTrack,
  shortfall,
}: {
  name: string;
  current: string;
  target: string;
  progress: string;
  coverageLabel: string;
  requiredMonthly: string;
  onTrack: boolean;
  shortfall: string;
}) {
  const width = Math.min(100, Math.max(0, Number(progress) * 100));
  return (
    <div className="space-y-3 rounded-md border border-line bg-surface p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">{name}</h2>
          <p className="mt-1 text-sm text-muted">{coverageLabel}</p>
        </div>
        <p className="text-sm text-muted">
          <MoneyAmount amount={current} /> of <MoneyAmount amount={target} />
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-subtle">
        <div className={`h-full ${onTrack ? "bg-healthy" : "bg-warning"}`} style={{ width: `${width}%` }} />
      </div>
      <p className="text-xs text-muted">
        Required monthly <MoneyAmount amount={requiredMonthly} />
        {shortfall !== "0.00" ? (
          <>
            {" "}
            · shortfall <MoneyAmount amount={shortfall} />
          </>
        ) : null}
      </p>
    </div>
  );
}
