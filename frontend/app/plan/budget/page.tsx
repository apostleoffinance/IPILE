"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AlertList } from "@/components/plan/AlertList";
import { BudgetForm } from "@/components/plan/BudgetForm";
import { BudgetProgress } from "@/components/plan/BudgetProgress";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Select } from "@/components/ui/select";
import { api, type Alert, type Budget, type Category, type Member } from "@/lib/api";

export default function BudgetPage() {
  return (
    <AppShell>
      <Suspense fallback={<LoadingState />}>
        <BudgetPageBody />
      </Suspense>
    </AppShell>
  );
}

function BudgetPageBody() {
  const searchParams = useSearchParams();
  const defaultMemberId = searchParams.get("member") ?? undefined;
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [period, setPeriod] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [nextBudgets, nextAlerts, nextCategories, nextMembers] = await Promise.all([
      api.budgets(),
      api.alerts(),
      api.categories(),
      api.members(),
    ]);
    setBudgets(nextBudgets);
    setAlerts(nextAlerts);
    setCategories(nextCategories);
    setMembers(nextMembers);
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  const periods = useMemo(() => {
    const unique = Array.from(new Set(budgets.map((budget) => budget.start_date)));
    return unique.sort().reverse();
  }, [budgets]);

  const visible = useMemo(
    () => (period === "all" ? budgets : budgets.filter((budget) => budget.start_date === period)),
    [budgets, period],
  );

  return (
    <ContentContainer>
      <PageHeader
        eyebrow="Plan"
        title="Budget"
        description="Are we spending according to plan?"
      />
      {error ? <ErrorState message={error} /> : null}
      {!loaded && !error ? <LoadingState /> : null}

      {alerts.length > 0 ? (
        <section>
          <SectionHeader title="Alerts" />
          <AlertList
            alerts={alerts}
            onRead={async (id) => {
              try {
                await api.readAlert(id);
                await refresh();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Could not update alert.");
              }
            }}
          />
        </section>
      ) : null}

      <SectionHeader title="Create budget" />
      <BudgetForm
        categories={categories}
        members={members}
        defaultMemberId={defaultMemberId}
        pending={pending}
        onSubmit={async (draft) => {
          setPending(true);
          setError(null);
          try {
            await api.createBudget(draft);
            await refresh();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Could not create budget.");
          } finally {
            setPending(false);
          }
        }}
      />

      {periods.length > 1 ? (
        <label className="block max-w-xs text-sm">
          Period
          <Select
            className="mt-1"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          >
            <option value="all">All periods</option>
            {periods.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </label>
      ) : null}

      <SectionHeader title="Plans" />
      {loaded && visible.length === 0 ? (
        <EmptyState title="No budgets yet" body="Create a household or member-scoped plan to track spend." />
      ) : (
        visible.map((budget) => (
          <section key={budget.id} className="border border-line bg-surface p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <h2 className="font-display text-2xl text-ink">{budget.name}</h2>
                <p className="mt-1 text-sm text-muted">
                  {budget.member_name ? `${budget.member_name} · ` : "Household · "}
                  {budget.start_date} to {budget.end_date}
                </p>
              </div>
              <p className="text-sm text-muted">
                <MoneyAmount amount={budget.spent_total} /> of{" "}
                <MoneyAmount amount={budget.allocated_total} />
              </p>
            </div>
            <div className="mt-6 space-y-5">
              {budget.categories.map((line) => (
                <BudgetProgress
                  key={line.id}
                  categoryName={line.category_name}
                  allocated={line.allocated_amount}
                  spent={line.spent_amount}
                  remaining={line.remaining_amount}
                  utilization={line.utilization}
                  status={line.status}
                />
              ))}
            </div>
          </section>
        ))
      )}
    </ContentContainer>
  );
}
