import Link from "next/link";
import { MoneyAmount } from "@/components/financial/MoneyAmount";

export function WealthSummary({
  netWorth,
  investments,
  emergency,
  debt,
  currency,
}: {
  netWorth: string;
  investments: string;
  emergency: string;
  debt: string;
  currency: string;
}) {
  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm uppercase tracking-wide text-muted">Wealth</h2>
        <Link href="/wealth" className="text-sm text-muted underline">
          Are we getting richer?
        </Link>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Metric label="Net worth" amount={netWorth} currency={currency} />
        <Metric label="Investments" amount={investments} currency={currency} />
        <Metric label="Emergency" amount={emergency} currency={currency} />
        <Metric label="Debt" amount={debt} currency={currency} />
      </div>
    </section>
  );
}

function Metric({ label, amount, currency }: { label: string; amount: string; currency: string }) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-xl">
        <MoneyAmount amount={amount} currency={currency} />
      </p>
    </div>
  );
}
