"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { NetWorthChart } from "@/components/charts/NetWorthChart";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { NetWorthSummary } from "@/components/financial/NetWorthSummary";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
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
      <ContentContainer>
        <PageHeader
          eyebrow="Wealth"
          title="Net worth"
          description="Are we getting richer?"
          actions={
            <div className="flex gap-3 text-sm">
              <Link href="/wealth/investments" className="text-muted underline">
                Investments
              </Link>
              <Link href="/wealth/goals" className="text-muted underline">
                Goals
              </Link>
              <Link href="/wealth/debts" className="text-muted underline">
                Debts
              </Link>
            </div>
          }
        />
        {error ? <ErrorState message={error} /> : null}
        {!data && !error ? <LoadingState /> : null}
        {data ? (
          <>
            <NetWorthSummary
              netWorth={data.net_worth}
              totalAssets={data.total_assets}
              totalLiabilities={data.total_liabilities}
              currency={data.currency}
            />
            <p className="text-sm text-muted">
              Emergency fund{" "}
              <MoneyAmount amount={data.emergency_fund} currency={data.currency} />
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="border border-line bg-surface p-5">
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
              <div className="border border-line bg-surface p-5">
                <h2 className="text-sm uppercase tracking-wide text-muted">Liabilities</h2>
                <Row label="Loans" amount={data.buckets.loans} />
                <Row label="Credit" amount={data.buckets.credit} />
                <Row label="Other" amount={data.buckets.other_debt} />
                <Row label="Total debt" amount={data.debt} strong />
              </div>
            </div>
            <section>
              <SectionHeader title="Net worth over time" />
              {!data.history.length ? (
                <EmptyState title="No snapshots yet" body="Period close writes the first point on this chart." />
              ) : (
                <NetWorthChart
                  points={data.history.map((row) => ({
                    label: row.period_start.slice(0, 7),
                    net_worth: row.net_worth,
                  }))}
                />
              )}
            </section>
            <SectionHeader title="Add asset" />
            <form onSubmit={onCreate} className="grid gap-3 border border-line bg-surface p-5 md:grid-cols-4">
              <Input placeholder="Asset name" value={name} onChange={(event) => setName(event.target.value)} />
              <Select
                className="text-sm"
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
              </Select>
              <Input
                className="tabular"
                placeholder="Current value"
                value={value}
                onChange={(event) => setValue(event.target.value)}
              />
              <Button type="submit" disabled={pending}>
                Add asset
              </Button>
            </form>
          </>
        ) : null}
      </ContentContainer>
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
