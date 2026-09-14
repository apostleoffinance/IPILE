import { MoneyAmount } from "@/components/financial/MoneyAmount";
import type { AllocationLine } from "@/lib/api";

export function AllocationBar({
  lines,
  currency,
}: {
  lines: AllocationLine[];
  currency: string;
}) {
  const total = lines.reduce((sum, line) => sum + Number(line.amount), 0);
  return (
    <div className="space-y-3">
      <div className="flex h-3 overflow-hidden rounded-full bg-subtle">
        {lines.map((line) => {
          const width = total > 0 ? (Number(line.amount) / total) * 100 : 0;
          if (width <= 0) return null;
          return (
            <div
              key={line.id}
              className={`h-full ${line.funded ? "bg-accent/70" : "bg-critical/60"}`}
              style={{ width: `${width}%` }}
              title={`${line.name} ${line.amount}`}
            />
          );
        })}
      </div>
      <ul className="space-y-2">
        {lines.map((line) => (
          <li key={line.id} className="flex items-baseline justify-between text-sm">
            <span>
              {line.name}
              {!line.funded ? <span className="ml-2 text-xs text-critical">underfunded</span> : null}
            </span>
            <MoneyAmount amount={line.amount} currency={currency} />
          </li>
        ))}
      </ul>
    </div>
  );
}
