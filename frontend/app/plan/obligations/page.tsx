"use client";

import { useEffect, useState } from "react";
import { DecisionCard } from "@/components/financial/DecisionCard";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ObligationCard } from "@/components/financial/ObligationCard";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { ObligationForm } from "@/components/plan/ObligationForm";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { api, type Account, type CalendarEvent, type Obligation } from "@/lib/api";

export default function ObligationsPage() {
  const currency = useHouseholdCurrency();
  const [items, setItems] = useState<Obligation[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextItems, nextEvents, nextAccounts] = await Promise.all([
      api.obligations(),
      api.calendar(30),
      api.accounts(),
    ]);
    setItems(nextItems);
    setEvents(nextEvents);
    setAccounts(nextAccounts);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  const unfunded = events.filter((event) => event.coverage_label && event.coverage_label !== "funded");

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Plan"
          title="Obligations"
          description="Are we prepared for what is coming?"
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        {unfunded.length > 0 ? (
          <section className="space-y-3">
            <SectionHeader title="Needs attention" />
            {unfunded.slice(0, 3).map((event) => (
              <DecisionCard
                key={event.id}
                title={`${event.title} needs funding`}
                body={`Due ${event.date} · ${event.coverage_label}`}
                href="/plan/obligations"
                severity="warning"
              />
            ))}
          </section>
        ) : null}

        <section>
          <SectionHeader title="Next 30 days" description="Financial obligations on the calendar." />
          {events.length === 0 ? (
            <EmptyState title="Nothing due in 30 days" body="Generated occurrences will land on this strip." />
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <ObligationCard key={event.id} event={event} currency={currency ?? "NGN"} href="#list" />
              ))}
            </div>
          )}
        </section>

        <section id="list">
          <SectionHeader title="Add obligation" />
          <ObligationForm
            pending={pending}
            onSubmit={async (draft) => {
              setPending(true);
              setError(null);
              try {
                await api.createObligation(draft);
                await refresh();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Could not save.");
              } finally {
                setPending(false);
              }
            }}
          />
        </section>

        {loaded && items.length === 0 ? (
          <EmptyState title="No obligations" body="Add rent, fees, or support the household must fund." />
        ) : (
          items.map((item) => (
            <section key={item.id} className="border border-line bg-surface p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div>
                  <h2 className="font-display text-2xl text-ink">{item.name}</h2>
                  <p className="mt-1 text-sm capitalize text-muted">
                    {item.frequency} · {item.priority}
                    {item.fund_name ? ` · ${item.fund_name}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm">
                    <MoneyAmount amount={item.amount} currency={item.currency} />
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    <MoneyAmount amount={item.required_monthly} currency={item.currency} /> / mo
                    {item.next_occurrence ? ` · ${item.next_occurrence.coverage_label}` : ""}
                  </p>
                </div>
              </div>
              <div className="mt-4 space-y-2 text-sm">
                {item.occurrences.slice(0, 6).map((occurrence) => (
                  <div key={occurrence.id} className="flex items-center justify-between gap-3">
                    <p className="text-muted">
                      {occurrence.due_date} · {occurrence.status} · {occurrence.coverage_label}
                    </p>
                    {occurrence.status !== "paid" && occurrence.status !== "skipped" && accountId ? (
                      <Button
                        type="button"
                        variant="link"
                        className="h-auto p-0 text-xs"
                        onClick={async () => {
                          try {
                            await api.payOccurrence(item.id, occurrence.id, accountId);
                            await refresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Could not pay.");
                          }
                        }}
                      >
                        Pay
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ))
        )}
      </ContentContainer>
    </AppShell>
  );
}
