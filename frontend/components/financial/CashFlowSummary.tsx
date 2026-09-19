import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { MoneyChange } from "@/components/financial/MoneyChange";
import type { CashFlow } from "@/lib/api";
import { cn } from "@/lib/utils";

export function CashFlowSummary({
  data,
  className,
}: {
  data: CashFlow;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)} aria-label="Cash flow summary">
      <Metric label="Opening cash" amount={data.opening_cash} />
      <Metric label="Closing cash" amount={data.closing_cash} />
      <Metric label="Income" amount={data.income} />
      <Metric label="Expenses" amount={data.expenses} />
      <Metric label="Giving" amount={data.giving} />
      <Metric label="Transfers net" amount={data.transfers_net} signed />
      <Metric label="Surplus" amount={data.surplus} signed />
    </section>
  );
}

function Metric({
  label,
  amount,
  signed = false,
}: {
  label: string;
  amount: string;
  signed?: boolean;
}) {
  return (
    <div className="border border-line bg-surface px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-xl">
        {signed ? <MoneyChange amount={amount} /> : <MoneyAmount amount={amount} />}
      </p>
    </div>
  );
}
