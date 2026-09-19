"use client";

import { useEffect, useState } from "react";
import { CashFlowChart } from "@/components/charts/CashFlowChart";
import { CashFlowSummary } from "@/components/financial/CashFlowSummary";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { getCashFlow, type CashFlow } from "@/lib/api";

export default function CashFlowPage() {
  const [data, setData] = useState<CashFlow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getCashFlow()
      .then((payload) => {
        setData(payload);
        setLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Money"
          title="Cash flow"
          description="How did cash move this period? Opening to closing, day by day."
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {data ? (
          <>
            <p className="text-sm text-muted">
              {data.period_start} → {data.period_end}
            </p>
            <CashFlowSummary data={data} />
            <SectionHeader title="Daily movement" description="Income, outflows, and closing cash." />
            {!data.daily.length ? (
              <EmptyState title="No daily activity" body="Transactions in this period will appear as a day series." />
            ) : (
              <>
                <CashFlowChart days={data.daily} />
                <div className="overflow-x-auto border border-line">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-line bg-subtle text-muted">
                      <tr>
                        <th className="px-3 py-2 font-medium">Date</th>
                        <th className="px-3 py-2 font-medium">Income</th>
                        <th className="px-3 py-2 font-medium">Expenses</th>
                        <th className="px-3 py-2 font-medium">Giving</th>
                        <th className="px-3 py-2 font-medium">Net</th>
                        <th className="px-3 py-2 font-medium">Cash</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.daily.map((row) => (
                        <tr key={row.date} className="border-b border-line last:border-0">
                          <td className="px-3 py-2">{row.date}</td>
                          <td className="px-3 py-2">
                            <MoneyAmount amount={row.income} />
                          </td>
                          <td className="px-3 py-2">
                            <MoneyAmount amount={row.expenses} />
                          </td>
                          <td className="px-3 py-2">
                            <MoneyAmount amount={row.giving} />
                          </td>
                          <td className="px-3 py-2">
                            <MoneyAmount amount={row.net} />
                          </td>
                          <td className="px-3 py-2">
                            <MoneyAmount amount={row.closing_cash} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}
