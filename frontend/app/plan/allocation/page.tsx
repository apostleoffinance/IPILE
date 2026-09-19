"use client";

import { useEffect, useState } from "react";
import { AllocationBar } from "@/components/allocation/AllocationBar";
import { AllocationChart } from "@/components/charts/AllocationChart";
import { DecisionCard } from "@/components/financial/DecisionCard";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import {
  getAllocationRules,
  getLatestAllocation,
  runAllocation,
  type AllocationRule,
  type AllocationRun,
} from "@/lib/api";

export default function AllocationPage() {
  const currency = useHouseholdCurrency();
  const [rules, setRules] = useState<AllocationRule[]>([]);
  const [run, setRun] = useState<AllocationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextRules, nextRun] = await Promise.all([getAllocationRules(), getLatestAllocation()]);
    setRules(nextRules);
    setRun(nextRun);
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Plan"
          title="Money plan"
          description="How should income be distributed? Rules are data, not hardcoded policy."
          actions={
            <Button
              type="button"
              disabled={pending}
              onClick={async () => {
                setPending(true);
                setError(null);
                try {
                  setRun(await runAllocation());
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Could not run allocation.");
                } finally {
                  setPending(false);
                }
              }}
            >
              {pending ? "Running..." : "Run allocation"}
            </Button>
          }
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        {run?.unfunded_mandatory?.length ? (
          <section className="space-y-3">
            {run.unfunded_mandatory.map((row) => (
              <DecisionCard
                key={`${row.rule_id}-${row.name}`}
                title={`${row.name} is underfunded`}
                body={`Requested ${row.requested_amount}; allocated ${row.amount}.`}
                href="/plan/allocation"
                severity="critical"
              />
            ))}
          </section>
        ) : null}

        <section>
          <SectionHeader title="Latest run" />
          {!run?.lines.length ? (
            <EmptyState title="No run yet" body="Record income or run allocation for this period." />
          ) : (
            <div className="space-y-4 border border-line bg-surface p-5">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Recognized income</p>
                  <p className="mt-1 text-xl">
                    <MoneyAmount amount={run.recognized_income} />
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Allocated</p>
                  <p className="mt-1 text-xl">
                    <MoneyAmount amount={run.total_allocated} />
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">Surplus after remainder</p>
                  <p className="mt-1 text-xl">
                    <MoneyAmount amount={run.surplus} />
                  </p>
                </div>
              </div>
              <AllocationChart lines={run.lines} />
              <AllocationBar lines={run.lines} currency={currency ?? "NGN"} />
            </div>
          )}
        </section>

        <section>
          <SectionHeader title="Rules" />
          {!rules.length ? (
            <EmptyState title="No rules" body="Household allocation rules are data, not hardcoded policy." />
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-baseline justify-between border border-line bg-surface px-4 py-3"
                >
                  <div>
                    <p className="text-sm">
                      {rule.priority}. {rule.name}
                    </p>
                    <p className="mt-1 text-xs capitalize text-muted">
                      {rule.type}
                      {rule.rate ? ` · ${rule.rate}` : ""}
                      {rule.mandatory ? " · mandatory" : ""}
                      {` · ${rule.destination_type}`}
                    </p>
                  </div>
                  <span className="text-sm">
                    {rule.type === "percentage" && rule.rate
                      ? `${Number(rule.rate) * 100}%`
                      : rule.amount
                        ? rule.amount
                        : "remainder"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </ContentContainer>
    </AppShell>
  );
}
