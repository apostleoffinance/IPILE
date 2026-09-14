"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { createAsset, getNetWorth, type WealthSnapshot } from "@/lib/api";

export default function WealthPage() {
  const [data, setData] = useState<WealthSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState("property");
  const [value, setValue] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    setData(await getNetWorth());
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createAsset({ name, type, current_value: value });
      setName("");
      setValue("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add asset.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-muted">Are we getting richer?</p>
            <h1 className="mt-1 text-3xl font-medium">Net worth</h1>
          </div>
          <div className="flex gap-4 text-sm">
            <Link href="/wealth/investments" className="underline text-muted">
              Investments
            </Link>
            <Link href="/wealth/goals" className="underline text-muted">
              Goals
            </Link>
            <Link href="/wealth/debts" className="underline text-muted">
              Debts
            </Link>
          </div>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!data && !error ? <LoadingState /> : null}
        {data ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-md border border-line bg-surface p-5">
                <h2 className="text-sm uppercase tracking-wide text-muted">Assets</h2>
                <Row label="Cash" amount={data.buckets.cash} />
                <Row label="Savings" amount={data.buckets.savings} />
                <Row label="Investments" amount={data.buckets.investments} />
                <Row label="Business" amount={data.buckets.business} />
                <Row label="Property" amount={data.buckets.property} />
                <Row label="Vehicle" amount={data.buckets.vehicle} />
                <Row label="Other" amount={data.buckets.other} />
                <Row label="Total assets" amount={data.total_assets} strong />
              </div>
              <div className="rounded-md border border-line bg-surface p-5">
                <h2 className="text-sm uppercase tracking-wide text-muted">Liabilities</h2>
                <Row label="Loans" amount={data.buckets.loans} />
                <Row label="Credit" amount={data.buckets.credit} />
                <Row label="Other" amount={data.buckets.other_debt} />
                <Row label="Total debt" amount={data.debt} strong />
              </div>
            </div>
            <div className="rounded-md border border-line bg-surface p-6 text-center">
              <p className="text-xs uppercase tracking-wide text-muted">Net worth</p>
              <p className="mt-2 text-4xl">
                <MoneyAmount amount={data.net_worth} currency={data.currency} />
              </p>
              <p className="mt-2 text-sm text-muted">
                Emergency <MoneyAmount amount={data.emergency_fund} currency={data.currency} />
              </p>
            </div>
            <section>
              <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Net worth over time</h2>
              {!data.history.length ? (
                <EmptyState title="No snapshots yet" body="Period close writes the first point on this chart." />
              ) : (
                <div className="space-y-2">
                  {data.history.map((row) => (
                    <div
                      key={row.period_start}
                      className="flex items-baseline justify-between rounded-md border border-line bg-surface px-4 py-3"
                    >
                      <p className="text-sm text-muted">
                        {row.period_start} → {row.period_end}
                      </p>
                      <MoneyAmount amount={row.net_worth} currency={data.currency} />
                    </div>
                  ))}
                </div>
              )}
            </section>
            <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
              <input
                className="rounded-md border border-line bg-canvas px-3 py-2"
                placeholder="Asset name"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              <select
                className="rounded-md border border-line bg-canvas px-3 py-2"
                value={type}
                onChange={(event) => setType(event.target.value)}
              >
                <option value="cash">Cash</option>
                <option value="savings">Savings</option>
                <option value="investment">Investment</option>
                <option value="business">Business</option>
                <option value="property">Property</option>
                <option value="vehicle">Vehicle</option>
                <option value="other">Other</option>
              </select>
              <input
                className="rounded-md border border-line bg-canvas px-3 py-2"
                placeholder="Current value"
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
              <button
                type="submit"
                disabled={pending}
                className="rounded-md bg-ink px-4 py-2 text-canvas disabled:opacity-50"
              >
                Add asset
              </button>
            </form>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}

function Row({ label, amount, strong }: { label: string; amount: string; strong?: boolean }) {
  return (
    <div className={`mt-3 flex items-baseline justify-between ${strong ? "pt-3" : ""}`}>
      <p className={`text-sm ${strong ? "font-medium" : "text-muted"}`}>{label}</p>
      <MoneyAmount amount={amount} />
    </div>
  );
}
