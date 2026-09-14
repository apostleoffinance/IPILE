"use client";

import { useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
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
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">What should we remember?</p>
          <h1 className="mt-1 text-3xl font-medium">Reports</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {kinds.map((row) => (
            <button
              key={row}
              type="button"
              onClick={() => setKind(row)}
              className={`rounded-md px-3 py-1.5 text-sm capitalize ${
                kind === row ? "bg-ink text-canvas" : "border border-line bg-surface text-muted"
              }`}
            >
              {row}
            </button>
          ))}
        </div>
        {pending ? <LoadingState /> : null}
        {error ? <ErrorState message={error} /> : null}
        {report && !pending ? <ReportBody report={report} /> : null}
      </div>
    </AppShell>
  );
}

function ReportBody({ report }: { report: Report }) {
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
    <article className="space-y-6 rounded-md border border-line bg-surface p-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">{String(payload.title ?? report.kind)}</p>
        <h2 className="mt-1 text-2xl">{String(payload.period_label ?? report.period_start)}</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {moneyKeys.map((key) =>
          typeof payload[key] === "string" ? (
            <div key={key} className="flex justify-between text-sm">
              <span className="capitalize text-muted">{key.replaceAll("_", " ")}</span>
              <MoneyAmount amount={payload[key] as string} currency="NGN" />
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
          <MoneyAmount amount={(payload.top_overspend as { amount: string }).amount} currency="NGN" />
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
      {typeof payload.shock === "string" && payload.shock ? (
        <p className="text-sm text-muted">Pilot shock: {payload.shock}</p>
      ) : null}
    </article>
  );
}
