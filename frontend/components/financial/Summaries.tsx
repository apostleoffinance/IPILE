import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { MoneyChange } from "@/components/financial/MoneyChange";
import type { GivingSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

export function GivingSummaryCard({
  summary,
  className,
}: {
  summary: GivingSummary;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-3 sm:grid-cols-2 lg:grid-cols-4", className)} aria-label="Giving summary">
      <Metric label="Posted this month" amount={summary.total_posted_month} />
      <Metric label="Posted this year" amount={summary.total_posted_year} />
      <Metric label="Policies" value={String(summary.policies.length)} />
      <Metric label="Pending approvals" value={String(summary.pending_approvals.length)} tone="warning" />
    </section>
  );
}

export function IncomeSummaryCard({
  expected,
  received,
  sourceCount,
  currency = "NGN",
  className,
}: {
  expected: string;
  received: string;
  sourceCount: number;
  currency?: string;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-3 sm:grid-cols-3", className)} aria-label="Income summary">
      <SummaryMetric label="Expected this period" amount={expected} currency={currency} />
      <SummaryMetric label="Received this period" amount={received} currency={currency} />
      <SummaryMetric label="Income sources" value={String(sourceCount)} />
    </section>
  );
}

function SummaryMetric({
  label,
  amount,
  value,
  currency = "NGN",
}: {
  label: string;
  amount?: string;
  value?: string;
  currency?: string;
}) {
  return (
    <div className="border border-line bg-surface px-4 py-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-2xl tabular">{amount != null ? <MoneyAmount amount={amount} currency={currency} /> : value}</p>
    </div>
  );
}

function Metric({
  label,
  amount,
  value,
  tone,
}: {
  label: string;
  amount?: string;
  value?: string;
  tone?: "warning";
}) {
  return (
    <div className="border border-line bg-surface px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={cn("mt-2 text-xl", tone === "warning" && Number(value) > 0 && "text-warning")}>
        {amount != null ? <MoneyAmount amount={amount} /> : value}
      </p>
    </div>
  );
}

export function DebtSummaryCard({
  totalDebt,
  currency = "NGN",
  openCount,
  className,
}: {
  totalDebt: string;
  currency?: string;
  openCount: number;
  className?: string;
}) {
  return (
    <section
      className={cn("grid gap-3 sm:grid-cols-2", className)}
      aria-label="Debt summary"
    >
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Total debt</p>
        <p className="mt-2 text-2xl">
          <MoneyAmount amount={totalDebt} currency={currency} />
        </p>
      </div>
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Open liabilities</p>
        <p className="mt-2 text-2xl tabular">{openCount}</p>
      </div>
    </section>
  );
}

export function InvestmentSummaryCard({
  totalValue,
  currency = "NGN",
  count,
  className,
}: {
  totalValue: string;
  currency?: string;
  count: number;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-3 sm:grid-cols-2", className)} aria-label="Investment summary">
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Portfolio value</p>
        <p className="mt-2 text-2xl">
          <MoneyAmount amount={totalValue} currency={currency} />
        </p>
      </div>
      <div className="border border-line bg-surface px-4 py-4">
        <p className="text-xs uppercase tracking-wide text-muted">Holdings</p>
        <p className="mt-2 text-2xl tabular">{count}</p>
      </div>
    </section>
  );
}

/** Re-export for pages that want signed change next to a summary. */
export { MoneyChange };
