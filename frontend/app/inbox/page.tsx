"use client";

import { useEffect, useState } from "react";
import { AlertList } from "@/components/plan/AlertList";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  getNotifications,
  markNotificationRead,
  runAutomationTick,
  type Notification,
} from "@/lib/api";

export default function InboxPage() {
  const [rows, setRows] = useState<Notification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState(false);

  async function refresh() {
    const next = await getNotifications();
    setRows(next);
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onRead(id: string) {
    await markNotificationRead(id);
    await refresh();
  }

  async function onTick() {
    setPending(true);
    setError(null);
    try {
      await runAutomationTick({ tick_type: "daily" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tick failed.");
    } finally {
      setPending(false);
    }
  }

  const alerts = rows.map((row) => ({
    id: row.id,
    household_id: row.household_id,
    type: "notification",
    severity: row.severity,
    title: row.title,
    body: row.body,
    related_entity_type: "notification",
    related_entity_id: row.id,
    period_key: "",
    status: row.status,
  }));

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-muted">What needs attention?</p>
            <h1 className="mt-1 text-3xl font-medium">Inbox</h1>
          </div>
          <button
            type="button"
            disabled={pending}
            onClick={onTick}
            className="rounded-md border border-line bg-surface px-4 py-2 text-sm disabled:opacity-50"
          >
            {pending ? "Running…" : "Run daily automation"}
          </button>
        </div>
        {!loaded && !error ? <LoadingState /> : null}
        {error ? <ErrorState message={error} /> : null}
        {loaded && !rows.length ? (
          <EmptyState title="Inbox clear" body="Alerts from budgets and obligations appear here." />
        ) : null}
        {rows.length ? <AlertList alerts={alerts} onRead={onRead} /> : null}
      </div>
    </AppShell>
  );
}
