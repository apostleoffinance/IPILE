"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, type Account, type CalendarEvent, type Obligation } from "@/lib/api";

export default function ObligationsPage() {
  const [items, setItems] = useState<Obligation[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState("monthly");
  const [nextDue, setNextDue] = useState(new Date().toISOString().slice(0, 10));
  const [sinking, setSinking] = useState(false);
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

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.createObligation({
        name,
        amount,
        frequency,
        next_due_date: nextDue,
        sinking_fund: sinking,
      });
      setName("");
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">Are we prepared for what is coming?</p>
          <h1 className="mt-1 text-3xl font-medium">Obligations</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        <section>
          <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">
            Financial obligations due in next 30 days
          </h2>
          {events.length === 0 ? (
            <EmptyState title="Nothing due in 30 days" body="Generated occurrences will land on this calendar strip." />
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <div key={event.id} className="flex justify-between rounded-md border border-line bg-surface px-4 py-3 text-sm">
                  <span>
                    {event.date} · {event.title}
                  </span>
                  <MoneyAmount amount={event.amount} />
                </div>
              ))}
            </div>
          )}
        </section>

        <form onSubmit={onCreate} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            Name
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Amount
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="450000.00"
            />
          </label>
          <label className="block text-sm">
            Frequency
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={frequency}
              onChange={(event) => setFrequency(event.target.value)}
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="annual">Annual</option>
              <option value="weekly">Weekly</option>
              <option value="one_time">One time</option>
            </select>
          </label>
          <label className="block text-sm">
            Next due
            <input
              type="date"
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={nextDue}
              onChange={(event) => setNextDue(event.target.value)}
            />
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input type="checkbox" checked={sinking} onChange={(event) => setSinking(event.target.checked)} />
            Attach a sinking fund
          </label>
          <div>
            <button type="submit" disabled={pending} className="rounded-md bg-accent px-4 py-2 text-sm text-white disabled:opacity-60">
              {pending ? "Saving…" : "Add obligation"}
            </button>
          </div>
        </form>

        {loaded && items.length === 0 ? (
          <EmptyState title="No obligations" body="Add rent, fees, or support the household must fund." />
        ) : (
          items.map((item) => (
            <section key={item.id} className="rounded-md border border-line bg-surface p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div>
                  <h2 className="text-lg font-medium">{item.name}</h2>
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
                      <button
                        type="button"
                        className="text-xs text-accent underline"
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
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ))
        )}
      </div>
    </AppShell>
  );
}
