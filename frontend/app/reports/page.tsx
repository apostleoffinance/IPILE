"use client";

import { useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import {
  getAnnualReport,
  getGivingReport,
  getMonthlyReport,
  getQuarterlyReport,
  type Report,
} from "@/lib/api";

const kinds = ["monthly", "quarterly", "annual", "giving"] as const;

export default function ReportsPage() {
  const [kind, setKind] = useState<(typeof kinds)[number]>("monthly");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(true);
  const currency = useHouseholdCurrency();

  useEffect(() => {
    setPending(true);
    setError(null);
    const load =
      kind === "monthly"
        ? getMonthlyReport()
        : kind === "quarterly"
          ? getQuarterlyReport(2026, 3)
          : kind === "annual"
            ? getAnnualReport(2026)
            : getGivingReport(2026);
    load
      .then(setReport)
      .catch((err: Error) => setError(err.message))
      .finally(() => setPending(false));
  }, [kind]);

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Intelligence"
          title="Reports"
          description="What should we remember? Period reviews from engine snapshots."
        />
        <Tabs value={kind} onValueChange={(value) => setKind(value as (typeof kinds)[number])}>
          <TabsList>
            {kinds.map((row) => (
              <TabsTrigger key={row} value={row} className="capitalize">
                {row}
              </TabsTrigger>
            ))}
          </TabsList>
          {kinds.map((row) => (
            <TabsContent key={row} value={row}>
              {pending ? <LoadingState /> : null}
              {error ? <ErrorState message={error} /> : null}
              {report && !pending && kind === row ? <ReportBody report={report} currency={currency} /> : null}
            </TabsContent>
          ))}
        </Tabs>
      </ContentContainer>
    </AppShell>
  );
}

function ReportBody({ report, currency }: { report: Report; currency?: string }) {
  const payload = report.payload;
  const moneyKeys = [
    "income",
    "expenses",
    "savings",
    "investments",
    "giving",
    "debt_reduction",
    "surplus",
    "net_worth_change",
    "allocated",
    "actual",
    "limit",
    "vs_limit",
  ];
  return (
    <article className="space-y-6 border border-line bg-surface p-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">{String(payload.title ?? report.kind)}</p>
        <h2 className="mt-1 font-display text-3xl text-ink">
          {String(payload.period_label ?? report.period_start)}
        </h2>
      </div>
      <SectionHeader title="Figures" />
      <div className="grid gap-3 md:grid-cols-2">
        {moneyKeys.map((key) =>
          typeof payload[key] === "string" ? (
            <div key={key} className="flex justify-between border-b border-line py-2 text-sm last:border-0">
              <span className="capitalize text-muted">{key.replaceAll("_", " ")}</span>
              <MoneyAmount amount={payload[key] as string} currency={currency ?? "NGN"} />
            </div>
          ) : null,
        )}
      </div>
      {typeof payload.health_score === "string" ? (
        <p className="text-sm">
          Financial health {payload.health_score}/100
          {typeof payload.health_label === "string" ? ` · ${payload.health_label}` : ""}
        </p>
      ) : null}
      {payload.top_overspend && typeof payload.top_overspend === "object" ? (
        <p className="text-sm text-muted">
          Top overspend {(payload.top_overspend as { category: string }).category}{" "}
          <MoneyAmount amount={(payload.top_overspend as { amount: string }).amount} currency={currency ?? "NGN"} />
        </p>
      ) : null}
      {typeof payload.best_improvement === "string" ? (
        <p className="text-sm text-muted">Best improvement: {payload.best_improvement}</p>
      ) : null}
      {payload.upcoming_risk && typeof payload.upcoming_risk === "object" ? (
        <p className="text-sm text-muted">
          Upcoming risk {(payload.upcoming_risk as { title: string }).title} on{" "}
          {(payload.upcoming_risk as { date: string }).date}
        </p>
      ) : null}
    </article>
  );
}
