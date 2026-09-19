"use client";

import { useEffect, useMemo, useState } from "react";
import { ObligationCard } from "@/components/financial/ObligationCard";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { api, type CalendarEvent } from "@/lib/api";

function monthBounds(anchor: Date) {
  const start = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const end = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);
  return { start, end };
}

function iso(day: Date) {
  const year = day.getFullYear();
  const month = String(day.getMonth() + 1).padStart(2, "0");
  const date = String(day.getDate()).padStart(2, "0");
  return `${year}-${month}-${date}`;
}

export default function CalendarPage() {
  const currency = useHouseholdCurrency();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [cursor, setCursor] = useState(() => new Date());

  const { start, end } = useMemo(() => monthBounds(cursor), [cursor]);
  const daysAhead = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.ceil((end.getTime() - today.getTime()) / 86400000);
    return Math.max(diff, 1);
  }, [end]);

  useEffect(() => {
    api
      .calendar(Math.min(Math.max(daysAhead, 31), 730))
      .then((rows) => {
        setEvents(rows);
        setLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [daysAhead]);

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const event of events) {
      const list = map.get(event.date) ?? [];
      list.push(event);
      map.set(event.date, list);
    }
    return map;
  }, [events]);

  const cells = useMemo(() => {
    const leading = start.getDay();
    const totalDays = end.getDate();
    const blanks = Array.from({ length: leading }, () => null as number | null);
    const days = Array.from({ length: totalDays }, (_, index) => index + 1);
    return [...blanks, ...days];
  }, [start, end]);

  const monthLabel = cursor.toLocaleString(undefined, { month: "long", year: "numeric" });
  const monthEvents = useMemo(() => {
    const startKey = iso(start);
    const endKey = iso(end);
    return events.filter((event) => event.date >= startKey && event.date <= endKey);
  }, [events, start, end]);

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Intelligence"
          title="Financial calendar"
          description="What is due this month?"
          actions={
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
              >
                Previous
              </Button>
              <p className="min-w-[10rem] text-center text-sm font-medium">{monthLabel}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
              >
                Next
              </Button>
            </div>
          }
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {loaded && !events.length ? (
          <EmptyState
            title="Nothing scheduled"
            body="Obligations, recurring bills, funds, debts, and goals will land here."
          />
        ) : null}
        <div
          className="grid grid-cols-7 gap-px overflow-hidden border border-line bg-line"
          role="grid"
          aria-label={`Calendar for ${monthLabel}`}
        >
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((label) => (
            <div
              key={label}
              role="columnheader"
              className="bg-subtle px-2 py-2 text-center text-xs uppercase tracking-wide text-muted"
            >
              {label}
            </div>
          ))}
          {cells.map((day, index) => {
            if (day === null) {
              return <div key={`blank-${index}`} className="min-h-28 bg-canvas" role="gridcell" />;
            }
            const dateKey = iso(new Date(cursor.getFullYear(), cursor.getMonth(), day));
            const dayEvents = byDate.get(dateKey) ?? [];
            return (
              <div key={dateKey} className="min-h-28 bg-surface p-2" role="gridcell" aria-label={dateKey}>
                <p className="text-xs font-medium text-muted">{day}</p>
                <ul className="mt-1 space-y-1">
                  {dayEvents.map((event) => (
                    <li key={event.id} className="text-[11px] leading-snug">
                      <span className="capitalize text-muted">{event.kind.replaceAll("_", " ")}</span>
                      <span className="block truncate text-ink">{event.title}</span>
                      <MoneyAmount amount={event.amount} />
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        {monthEvents.length > 0 ? (
          <section>
            <SectionHeader title="This month" description="List view of the same events." />
            <div className="space-y-2">
              {monthEvents.map((event) => (
                <ObligationCard key={event.id} event={event} currency={currency ?? "NGN"} />
              ))}
            </div>
          </section>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}
