"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PurchaseCheckModal } from "@/components/allocation/PurchaseCheckModal";
import { SafeToSpend } from "@/components/financial/SafeToSpend";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { getSafeToSpend, type SafeToSpendSnapshot } from "@/lib/api";

export default function ForecastPage() {
  const [data, setData] = useState<SafeToSpendSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkOpen, setCheckOpen] = useState(false);

  useEffect(() => {
    const openCheck =
      typeof window !== "undefined" && new URLSearchParams(window.location.search).get("check") === "1";
    getSafeToSpend()
      .then((snap) => {
        setData(snap);
        if (openCheck) setCheckOpen(true);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <AppShell>
      {!data && !error ? <LoadingState /> : null}
      {error ? (
        <ContentContainer>
          <ErrorState message={error} />
        </ContentContainer>
      ) : null}
      {data ? (
        <ContentContainer>
          <PageHeader
            eyebrow="Intelligence"
            title="Forecast"
            description="What can we safely spend ahead?"
            actions={
              <Button type="button" variant="outline" size="sm" asChild>
                <Link href="/overview">Back to Home</Link>
              </Button>
            }
          />
          <SafeToSpend
            snapshot={{ ...data, current: data.forecast }}
            currency={data.currency}
            label={`Forecast Safe to Spend · ${data.horizon_days} days`}
            description="Expected income and commitments over the horizon, after your minimum buffer."
            onInspect={() => setCheckOpen(true)}
          />
          <p className="text-sm text-muted">
            Showing forecast Safe to Spend over {data.horizon_days} days. Current STS remains{" "}
            <MoneyAmount amount={data.current} currency={data.currency} />.
          </p>
          <section className="grid gap-3 md:grid-cols-3">
            <Metric label="Current" amount={data.current} currency={data.currency} />
            <Metric label="Period" amount={data.period} currency={data.currency} />
            <Metric label="Minimum buffer" amount={data.minimum_buffer_amount} currency={data.currency} />
          </section>
          <SectionHeader title="Components" description="Inputs to the Safe to Spend engine." />
          <div className="grid gap-2 md:grid-cols-2">
            {(
              [
                ["liquid_cash", "Liquid cash"],
                ["expected_income", "Expected income"],
                ["committed_obligations", "Committed obligations"],
                ["upcoming_bills", "Upcoming bills"],
                ["sinking_fund_requirements", "Sinking fund requirements"],
                ["protected_savings", "Protected savings"],
                ["pending_transactions", "Pending transactions"],
              ] as const
            ).map(([key, label]) => (
              <div
                key={key}
                className="flex items-baseline justify-between border border-line bg-surface px-4 py-3 text-sm"
              >
                <span className="text-muted">{label}</span>
                <MoneyAmount amount={data.components[key]} currency={data.currency} />
              </div>
            ))}
          </div>
          {checkOpen ? (
            <PurchaseCheckModal
              currency={data.currency}
              snapshot={data}
              onClose={() => setCheckOpen(false)}
            />
          ) : null}
        </ContentContainer>
      ) : null}
    </AppShell>
  );
}

function Metric({
  label,
  amount,
  currency,
}: {
  label: string;
  amount: string;
  currency: string;
}) {
  return (
    <div className="border border-line bg-surface px-4 py-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-2xl tabular">
        <MoneyAmount amount={amount} currency={currency} />
      </p>
    </div>
  );
}
