"use client";

import { useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  explainWithAi,
  getInsights,
  type Insights,
} from "@/lib/api";

export default function InsightsPage() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getInsights().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <AppShell>
      {!data && !error ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {data ? (
        <div className="space-y-8 pb-16">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-muted">What is the pattern?</p>
              <h1 className="mt-1 text-3xl font-medium">Insights</h1>
            </div>
            <button
              type="button"
              disabled={pending}
              className="rounded-md border border-line bg-surface px-4 py-2 text-sm disabled:opacity-50"
              onClick={async () => {
                setPending(true);
                setError(null);
                try {
                  const body = await explainWithAi();
                  setExplanation(body.explanation);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "AI explain failed.");
                } finally {
                  setPending(false);
                }
              }}
            >
              {pending ? "Explaining…" : "Explain with AI"}
            </button>
          </div>
          {explanation ? (
            <p className="rounded-md border border-line bg-surface p-4 text-sm">{explanation}</p>
          ) : null}
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Health history</h2>
            {!data.health_history.length ? (
              <EmptyState title="No scores yet" body="Period scores appear after snapshots exist." />
            ) : (
              <TrendTable
                rows={data.health_history.map((row) => [row.period_label, `${row.score} · ${row.label}`])}
              />
            )}
          </section>
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Cash-flow trend</h2>
            {!data.cash_flow.length ? (
              <EmptyState title="No cash-flow history" body="Freeze a period snapshot to start the series." />
            ) : (
              <div className="space-y-2">
                {data.cash_flow.map((row) => (
                  <div key={row.period_start} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
                    <span>{row.period_label}</span>
                    <span className="tabular">
                      Income <MoneyAmount amount={row.income} currency="NGN" /> · surplus{" "}
                      <MoneyAmount amount={row.surplus} currency="NGN" />
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Net-worth trend</h2>
            {!data.net_worth.length ? (
              <EmptyState title="No net-worth history" body="Snapshots carry net worth for the chart." />
            ) : (
              <div className="space-y-2">
                {data.net_worth.map((row) => (
                  <div key={row.period_start} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
                    <span>{row.period_label}</span>
                    <MoneyAmount amount={row.net_worth} currency="NGN" />
                  </div>
                ))}
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Spending this period</h2>
            {!data.spend.length ? (
              <EmptyState title="No spend yet" body="Expense and giving categories will rank here." />
            ) : (
              <div className="space-y-2">
                {data.top_categories.map((row) => (
                  <div key={row.category} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
                    <span>{row.category}</span>
                    <MoneyAmount amount={row.amount} currency="NGN" />
                  </div>
                ))}
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Overspend</h2>
            {!data.overspend.length ? (
              <EmptyState title="No overspend" body="Categories over plan will appear here." />
            ) : (
              <div className="space-y-2">
                {data.overspend.map((row) => (
                  <div key={row.category} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
                    <span>{row.category}</span>
                    <MoneyAmount amount={row.amount} currency="NGN" />
                  </div>
                ))}
              </div>
            )}
          </section>
          <section>
            <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Giving vs limit</h2>
            <div className="grid gap-3 md:grid-cols-3">
              <Metric label="Allocated" amount={data.giving.allocated} />
              <Metric label="Actual" amount={data.giving.actual} />
              <Metric label="Vs limit" amount={data.giving.vs_limit} />
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  );
}

function TrendTable({ rows }: { rows: [string, string][] }) {
  return (
    <div className="space-y-2">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
          <span>{label}</span>
          <span className="tabular">{value}</span>
        </div>
      ))}
    </div>
  );
}

function Metric({ label, amount }: { label: string; amount: string }) {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2">
        <MoneyAmount amount={amount} currency="NGN" />
      </p>
    </div>
  );
}
