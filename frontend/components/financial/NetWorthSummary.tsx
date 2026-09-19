import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { MoneyChange } from "@/components/financial/MoneyChange";
import { cn } from "@/lib/utils";

export function NetWorthSummary({
  netWorth,
  totalAssets,
  totalLiabilities,
  currency = "NGN",
  delta,
  className,
}: {
  netWorth: string;
  totalAssets: string;
  totalLiabilities: string;
  currency?: string;
  delta?: string;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-3 sm:grid-cols-3", className)} aria-label="Net worth summary">
      <div className="border border-line bg-surface px-4 py-4 sm:col-span-3 sm:text-center">
        <p className="text-xs uppercase tracking-wide text-muted">Net worth</p>
        <p className="mt-2 font-display text-4xl">
          <MoneyAmount amount={netWorth} currency={currency} />
        </p>
        {delta != null ? (
          <p className="mt-2 text-sm">
            Change <MoneyChange amount={delta} currency={currency} />
          </p>
        ) : null}
      </div>
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Assets</p>
        <p className="mt-2 text-xl">
          <MoneyAmount amount={totalAssets} currency={currency} />
        </p>
      </div>
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Liabilities</p>
        <p className="mt-2 text-xl">
          <MoneyAmount amount={totalLiabilities} currency={currency} />
        </p>
      </div>
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Equity</p>
        <p className="mt-2 text-xl">
          <MoneyAmount amount={netWorth} currency={currency} />
        </p>
      </div>
    </section>
  );
}

export function IncomeSummary({
  sources,
  className,
}: {
  sources: { id: string; name: string; expected_amount: string; frequency: string }[];
  className?: string;
}) {
  return (
    <section className={cn("grid gap-3 md:grid-cols-2", className)} aria-label="Income sources">
      {sources.map((source) => (
        <article key={source.id} className="border border-line bg-surface p-4">
          <p className="text-sm text-muted">{source.name}</p>
          <p className="mt-2 text-xl">
            <MoneyAmount amount={source.expected_amount} />
          </p>
          <p className="mt-1 text-xs capitalize text-muted">{source.frequency}</p>
        </article>
      ))}
    </section>
  );
}
