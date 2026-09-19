"use client";

import { useEffect, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AlertList } from "@/components/plan/AlertList";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
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
      <ContentContainer>
        <PageHeader
          eyebrow="Automation"
          title="Inbox"
          description="What needs attention?"
          actions={
            <Button type="button" variant="outline" disabled={pending} onClick={onTick}>
              {pending ? "Running..." : "Run daily automation"}
            </Button>
          }
        />
        {!loaded && !error ? <LoadingState /> : null}
        {error ? <ErrorState message={error} /> : null}
        {loaded && !rows.length ? (
          <EmptyState title="Inbox clear" body="Alerts from budgets and obligations appear here." />
        ) : null}
        {rows.length ? <AlertList alerts={alerts} onRead={onRead} /> : null}
      </ContentContainer>
    </AppShell>
  );
}
