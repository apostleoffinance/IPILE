"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AllocationBar } from "@/components/allocation/AllocationBar";
import { PurchaseCheckModal } from "@/components/allocation/PurchaseCheckModal";
import { DecisionCard } from "@/components/financial/DecisionCard";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ObligationCard } from "@/components/financial/ObligationCard";
import { SafeToSpend } from "@/components/financial/SafeToSpend";
import { TransactionRow } from "@/components/financial/TransactionRow";
import { HealthScore } from "@/components/health/HealthScore";
import { WhyHealthModal } from "@/components/health/WhyHealthModal";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { api, getOverview, type HouseholdOverview } from "@/lib/api";

export default function OverviewPage() {
  const [data, setData] = useState<HouseholdOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkOpen, setCheckOpen] = useState(false);
  const [whyOpen, setWhyOpen] = useState(false);
  const [greetingName, setGreetingName] = useState("there");

  useEffect(() => {
    getOverview().then(setData).catch((err: Error) => setError(err.message));
    api.me().then((me) => setGreetingName(me.display_name.split(" ")[0] || me.display_name));
  }, []);

  const attention = useMemo(() => {
    if (!data) return [];
    const items: {
      title: string;
      body: string;
      href: string;
      severity: "warning" | "neutral" | "info";
    }[] = [];
    for (const event of data.upcoming_obligations ?? []) {
      if (event.coverage_label && event.coverage_label !== "funded") {
        items.push({
          title: `${event.title} is coming up`,
          body: `Due ${event.date} · ${event.coverage_label}`,
          href: "/plan/obligations",
          severity: "warning",
        });
      }
    }
    if (!data.accounts.length) {
      items.push({
        title: "Let's find your money",
        body: "Add a bank, cash, or savings account so IPÌLẸ̀ can see your real position.",
        href: "/money/accounts",
        severity: "neutral",
      });
    } else if (data.period_income === "0.00") {
      items.push({
        title: "No income recorded this month",
        body: "Record income so IPÌLẸ̀ can allocate and update Safe to Spend.",
        href: "/money/income",
        severity: "neutral",
      });
    }
    if (data.foundation && data.foundation.completed < data.foundation.total) {
      items.push({
        title: `Your foundation is ${Math.round((data.foundation.completed / data.foundation.total) * 100)}% complete`,
        body: "Continue setup: accounts, income, obligations, money plan, and goals.",
        href: "/onboarding?continue=1",
        severity: "info",
      });
    }
    return items.slice(0, 4);
  }, [data]);

  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <AppShell>
      {!data && !error ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {data ? (
        <ContentContainer>
          <PageHeader
            eyebrow={today}
            title={`Good day, ${greetingName}`}
            description="Here's how your household is doing."
            actions={
              <Button type="button" variant="outline" size="sm" onClick={() => setCheckOpen(true)}>
                Check a purchase
              </Button>
            }
          />

          {data.safe_to_spend ? (
            <SafeToSpend
              snapshot={data.safe_to_spend}
              currency={data.currency}
              onInspect={() => setCheckOpen(true)}
            />
          ) : (
            <section className="border border-line bg-surface px-6 py-8">
              <p className="text-xs uppercase tracking-[0.25em] text-muted">Safe to spend</p>
              <p className="mt-3 font-display text-3xl text-ink">Not ready yet</p>
              <p className="mt-2 max-w-xl text-sm text-muted">
                Add accounts, income, and obligations so IPÌLẸ̀ can compute Safe to Spend from real data.
              </p>
            </section>
          )}

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Income this month" amount={data.period_income} currency={data.currency} />
            {data.allocated_total != null ? (
              <Metric label="Allocated" amount={data.allocated_total} currency={data.currency} />
            ) : null}
            <Metric label="Cash" amount={data.cash_total} currency={data.currency} />
            <Metric
              label="Net worth"
              amount={data.wealth?.net_worth ?? "0.00"}
              currency={data.currency}
            />
          </section>

          {data.wealth ? (
            <section className="grid gap-3 md:grid-cols-3">
              <Metric label="Emergency" amount={data.wealth.emergency_fund} currency={data.currency} />
              <Metric label="Debt" amount={data.wealth.debt} currency={data.currency} />
              <Metric label="Investments" amount={data.wealth.investments} currency={data.currency} />
            </section>
          ) : null}

          <section>
            {data.health_ready && data.health ? (
              <HealthScore health={data.health} onOpen={() => setWhyOpen(true)} />
            ) : (
              <div className="border border-line bg-surface p-5">
                <p className="text-xs uppercase tracking-wide text-muted">Financial health</p>
                <p className="mt-2 font-display text-2xl">Not enough data yet</p>
                <p className="mt-2 text-sm text-muted">
                  Add accounts and income to establish your household baseline. IPÌLẸ̀ won&apos;t invent
                  a score.
                </p>
              </div>
            )}
          </section>

          <section>
            <h2 className="font-display text-2xl text-ink">What needs your attention?</h2>
            <div className="mt-4 space-y-3">
              {attention.length === 0 ? (
                <p className="border border-line bg-surface px-4 py-3 text-sm text-muted">
                  Nothing urgent. Your household looks on track.
                </p>
              ) : (
                attention.map((item) => (
                  <DecisionCard
                    key={item.title}
                    title={item.title}
                    body={item.body}
                    href={item.href}
                    severity={item.severity}
                  />
                ))
              )}
            </div>
          </section>

          {data.foundation ? (
            <section className="border border-line bg-surface p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Your IPÌLẸ̀ foundation</p>
              <p className="mt-2 font-display text-3xl">
                {Math.round((data.foundation.completed / data.foundation.total) * 100)}%
              </p>
              <div className="mt-3 h-2 w-full bg-subtle">
                <div
                  className="h-2 bg-accent"
                  style={{
                    width: `${(data.foundation.completed / data.foundation.total) * 100}%`,
                  }}
                />
              </div>
              <ul className="mt-4 grid gap-2 text-sm md:grid-cols-3">
                {(
                  [
                    ["accounts", "Accounts"],
                    ["income", "Income"],
                    ["obligations", "Obligations"],
                    ["budget", "Money plan"],
                    ["goals", "Goals"],
                  ] as const
                ).map(([key, label]) => (
                  <li key={key} className={data.foundation?.[key] ? "text-accent" : "text-muted"}>
                    {data.foundation?.[key] ? "✓" : "○"} {label}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section>
            <div className="mb-3 flex items-end justify-between">
              <h2 className="font-display text-2xl">Money plan</h2>
              <Link href="/plan/allocation" className="text-sm text-accent underline">
                Edit rules
              </Link>
            </div>
            {!data.allocation?.lines.length ? (
              <EmptyState
                title="How should income be distributed?"
                body="Tell IPÌLẸ̀ where money should go when it arrives: giving, obligations, essentials, protection, goals."
                actionLabel="Set money plan"
                actionHref="/plan/allocation"
              />
            ) : (
              <AllocationBar lines={data.allocation.lines} currency={data.currency} />
            )}
          </section>

          <section>
            <h2 className="mb-3 font-display text-2xl">Coming up</h2>
            {!data.upcoming_obligations?.length ? (
              <EmptyState
                title="What must your household prepare for?"
                body="Add rent, school fees, family support, or anything with a due date."
                actionLabel="Add obligation"
                actionHref="/plan/obligations"
              />
            ) : (
              <div className="space-y-3">
                {data.upcoming_obligations.map((event) => (
                  <ObligationCard key={event.id} event={event} currency={data.currency} />
                ))}
              </div>
            )}
          </section>

          <section>
            <div className="mb-3 flex items-end justify-between">
              <h2 className="font-display text-2xl">Recent money</h2>
              <Link href="/money/transactions" className="text-sm text-accent underline">
                All activity
              </Link>
            </div>
            {data.recent_transactions.length === 0 ? (
              <EmptyState
                title="No movement yet"
                body="Record income or spending. IPÌLẸ̀ will update budgets and Safe to Spend automatically."
                actionLabel="Add transaction"
                actionHref="/money/transactions"
              />
            ) : (
              <div className="space-y-2">
                {data.recent_transactions.slice(0, 5).map((tx) => (
                  <TransactionRow key={tx.id} transaction={tx} />
                ))}
              </div>
            )}
          </section>

          {checkOpen && data.safe_to_spend ? (
            <PurchaseCheckModal
              currency={data.currency}
              snapshot={data.safe_to_spend}
              onClose={() => setCheckOpen(false)}
            />
          ) : null}
          {whyOpen && data.health ? (
            <WhyHealthModal fallback={data.health} onClose={() => setWhyOpen(false)} />
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
