"use client";

import { useEffect, useMemo, useState } from "react";
import { NetWorthChart } from "@/components/charts/NetWorthChart";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { explainWithAi, getInsights, type Insights } from "@/lib/api";
import { decisionHrefForPattern } from "@/lib/decision-routing";

export default function InsightsPage() {
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getInsights().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  const patternSeverity = useMemo(() => {
    return (severity: string) => {
      if (severity === "critical") return "critical" as const;
      if (severity === "warning") return "warning" as const;
      if (severity === "info") return "info" as const;
      return "neutral" as const;
    };
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
            title="Insights"
            description="What is the pattern? Deterministic figures first; AI only explains."
            actions={
              <Button
                type="button"
                variant="outline"
                disabled={pending}
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
                {pending ? "Explaining..." : "Explain with AI"}
              </Button>
            }
          />
          {explanation ? (
            <p className="border border-gold/30 bg-surface p-4 text-sm text-ink">{explanation}</p>
          ) : null}

          <Tabs defaultValue="patterns">
            <TabsList>
              <TabsTrigger value="patterns">Patterns</TabsTrigger>
              <TabsTrigger value="trends">Trends</TabsTrigger>
              <TabsTrigger value="spend">Spend</TabsTrigger>
              <TabsTrigger value="giving">Giving</TabsTrigger>
            </TabsList>

            <TabsContent value="patterns">
              <SectionHeader title="Patterns" description="Flags from engines, not invented narrative." />
              {!data.patterns?.length ? (
                <EmptyState
                  title="No patterns yet"
                  body="IPÌLẸ̀ flags overspend, giving limits, constitution gaps, and streaks here."
                />
              ) : (
                <div className="space-y-3">
                  {data.patterns.map((pattern) => (
                    <DecisionCard
                      key={pattern.code + pattern.title}
                      title={pattern.title}
                      body={`${pattern.detail} · ${pattern.code}`}
                      href={decisionHrefForPattern(pattern.code)}
                      severity={patternSeverity(pattern.severity)}
                    />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="trends" className="space-y-8">
              <section>
                <SectionHeader title="Net worth" />
                {!data.net_worth.length ? (
                  <EmptyState title="No net-worth history" body="Snapshots carry net worth for the chart." />
                ) : (
                  <NetWorthChart
                    points={data.net_worth.map((row) => ({
                      label: row.period_label,
                      net_worth: row.net_worth,
                    }))}
                  />
                )}
              </section>
              <section>
                <SectionHeader title="Cash-flow trend" />
                {!data.cash_flow.length ? (
                  <EmptyState title="No cash-flow history" body="Freeze a period snapshot to start the series." />
                ) : (
                  <div className="space-y-2">
                    {data.cash_flow.map((row) => (
                      <div
                        key={row.period_start}
                        className="flex justify-between border border-line bg-surface px-4 py-3 text-sm"
                      >
                        <span>{row.period_label}</span>
                        <span className="tabular">
                          Income <MoneyAmount amount={row.income} currency={data.currency ?? "NGN"} /> · surplus{" "}
                          <MoneyAmount amount={row.surplus} currency={data.currency ?? "NGN"} />
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section>
                <SectionHeader title="Health history" />
                {!data.health_history.length ? (
                  <EmptyState title="No scores yet" body="Period scores appear after snapshots exist." />
                ) : (
                  <div className="space-y-2">
                    {data.health_history.map((row) => (
                      <div
                        key={row.period_start}
                        className="flex justify-between border border-line bg-surface px-4 py-3 text-sm"
                      >
                        <span>{row.period_label}</span>
                        <span className="tabular">
                          {row.score} · {row.label}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </TabsContent>

            <TabsContent value="spend" className="space-y-8">
              <section>
                <SectionHeader title="Top categories" />
                {!data.spend.length ? (
                  <EmptyState title="No spend yet" body="Expense and giving categories will rank here." />
                ) : (
                  <div className="space-y-2">
                    {data.top_categories.map((row) => (
                      <div
                        key={row.category}
                        className="flex justify-between border border-line bg-surface px-4 py-3 text-sm"
                      >
                        <span>{row.category}</span>
                        <MoneyAmount amount={row.amount} currency={data.currency ?? "NGN"} />
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section>
                <SectionHeader title="Overspend" />
                {!data.overspend.length ? (
                  <EmptyState title="No overspend" body="Categories over plan will appear here." />
                ) : (
                  <div className="space-y-3">
                    {data.overspend.map((row) => (
                      <DecisionCard
                        key={row.category}
                        title={`${row.category} is over plan`}
                        body={`Over by the recorded amount. Open Budget to adjust the plan.`}
                        href="/plan/budget"
                        severity="warning"
                      />
                    ))}
                    {data.overspend.map((row) => (
                      <div
                        key={`${row.category}-amt`}
                        className="flex justify-between border border-line bg-surface px-4 py-3 text-sm"
                      >
                        <span>{row.category}</span>
                        <MoneyAmount amount={row.amount} currency={data.currency ?? "NGN"} />
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </TabsContent>

            <TabsContent value="giving">
              <SectionHeader title="Giving vs limit" />
              <div className="grid gap-3 md:grid-cols-3">
                <Metric label="Allocated" amount={data.giving.allocated} currency={data.currency} />
                <Metric label="Actual" amount={data.giving.actual} currency={data.currency} />
                <Metric label="Vs limit" amount={data.giving.vs_limit} currency={data.currency} />
              </div>
            </TabsContent>
          </Tabs>
        </ContentContainer>
      ) : null}
    </AppShell>
  );
}

function Metric({ label, amount, currency = "NGN" }: { label: string; amount: string; currency?: string }) {
  return (
    <div className="border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2">
        <MoneyAmount amount={amount} currency={currency} />
      </p>
    </div>
  );
}
