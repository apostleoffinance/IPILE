"use client";

import { useEffect, useState } from "react";
import { AllocationBar } from "@/components/allocation/AllocationBar";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  getAllocationRules,
  getLatestAllocation,
  runAllocation,
  type AllocationRule,
  type AllocationRun,
} from "@/lib/api";

export default function AllocationPage() {
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
      <div className="space-y-8 pb-16">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm text-muted">How should income be distributed?</p>
            <h1 className="mt-1 font-display text-3xl font-medium">Money plan</h1>
          </div>
          <button
            type="button"
            disabled={pending}
            className="rounded-md bg-ink px-4 py-2 text-sm text-canvas disabled:opacity-50"
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
            {pending ? "Running…" : "Run allocation"}
          </button>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        <section>
          <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Latest run</h2>
          {!run?.lines.length ? (
            <EmptyState title="No run yet" body="Record income or run allocation for this period." />
          ) : (
            <div className="space-y-4 rounded-md border border-line bg-surface p-5">
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
              <AllocationBar lines={run.lines} currency="NGN" />
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Rules</h2>
          {!rules.length ? (
            <EmptyState title="No rules" body="Household allocation rules are data, not hardcoded policy." />
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-baseline justify-between rounded-md border border-line bg-surface px-4 py-3"
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
      </div>
    </AppShell>
  );
}
