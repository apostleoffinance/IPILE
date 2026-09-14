import { MoneyAmount } from "@/components/financial/MoneyAmount";

export function MoneySummary({
  cashTotal,
  periodIncome,
  allocatedTotal,
  safeToSpend,
  currency,
  onOpenSafeToSpend,
}: {
  cashTotal: string;
  periodIncome: string;
  allocatedTotal: string;
  safeToSpend: string;
  currency: string;
  onOpenSafeToSpend?: () => void;
}) {
  return (
    <div className="space-y-4">
      <section className="rounded-md border border-line bg-surface p-5">
        <p className="text-xs uppercase tracking-wide text-muted">Cash</p>
        <p className="mt-2 text-3xl">
          <MoneyAmount amount={cashTotal} currency={currency} />
        </p>
        <p className="mt-1 text-sm text-muted">What the household physically has. Not Safe to Spend.</p>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-md border border-line bg-surface p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Income</p>
          <p className="mt-2 text-3xl">
            <MoneyAmount amount={periodIncome} currency={currency} />
          </p>
          <p className="mt-1 text-sm text-muted">Recognized this period.</p>
        </div>
        <div className="rounded-md border border-line bg-surface p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Allocated</p>
          <p className="mt-2 text-3xl">
            <MoneyAmount amount={allocatedTotal} currency={currency} />
          </p>
          <p className="mt-1 text-sm text-muted">Where recognized income is assigned.</p>
        </div>
        <button
          type="button"
          onClick={onOpenSafeToSpend}
          className="rounded-md border border-line bg-surface p-5 text-left"
        >
          <p className="text-xs uppercase tracking-wide text-muted">Safe to Spend</p>
          <p className="mt-2 text-3xl">
            <MoneyAmount amount={safeToSpend} currency={currency} />
          </p>
          <p className="mt-1 text-sm text-muted">Freedom after commitments. Open variants and purchase check.</p>
        </button>
      </section>
    </div>
  );
}
