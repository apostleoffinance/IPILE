"use client";

import { useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { getBusinesses, type HouseholdBusiness } from "@/lib/api";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";

export type BusinessSection = "revenue" | "expenses" | "pnl";

const sectionCopy: Record<BusinessSection, { title: string; description: string }> = {
  revenue: { title: "Business revenue", description: "What is the business generating?" },
  expenses: { title: "Business expenses", description: "What is the business consuming?" },
  pnl: { title: "Business P&L", description: "Is the business helping or hurting the household?" },
};

export function BusinessSectionPage({ section }: { section: BusinessSection }) {
  const [businesses, setBusinesses] = useState<HouseholdBusiness[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const currency = useHouseholdCurrency();
  const copy = sectionCopy[section];

  useEffect(() => {
    getBusinesses()
      .then(setBusinesses)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoaded(true));
  }, []);

  const business = businesses[0];

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Business"
          title={copy.title}
          description={copy.description}
          actions={<Button variant="outline" asChild><a href="/business">Open business workspace</a></Button>}
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {!business && loaded ? <EmptyState title="No business yet" body="Add a business in the workspace first." actionLabel="Open business" actionHref="/business" /> : null}
        {business ? <BusinessSection business={business} section={section} currency={currency ?? "NGN"} /> : null}
      </ContentContainer>
    </AppShell>
  );
}

function BusinessSection({ business, section, currency }: { business: HouseholdBusiness; section: BusinessSection; currency: string }) {
  if (section === "pnl") {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Revenue" amount={business.pnl.revenue} currency={currency} />
        <Metric label="Expenses" amount={business.pnl.expenses} currency={currency} />
        <Metric label="Profit" amount={business.pnl.profit} currency={currency} />
        <Metric label="Family return" amount={business.pnl.family_return} currency={currency} />
        <Metric label="Family invested" amount={business.pnl.family_invested} currency={currency} />
        <Metric label="Withdrawn" amount={business.pnl.family_withdrawn} currency={currency} />
        <Metric label="Business equity" amount={business.pnl.current_business_equity} currency={currency} />
      </div>
    );
  }

  const type = section === "revenue" ? "revenue" : "expense";
  const transactions = business.transactions.filter((transaction) => transaction.type === type);
  return transactions.length ? (
    <div className="space-y-2">
      {transactions.map((transaction) => (
        <div key={transaction.id} className="flex items-baseline justify-between border border-line bg-surface px-4 py-3">
          <div><p className="text-sm">{transaction.description ?? type}</p><p className="text-xs text-muted">{transaction.date}</p></div>
          <MoneyAmount amount={transaction.amount} currency={currency} />
        </div>
      ))}
    </div>
  ) : <EmptyState title={`No ${type} recorded`} body={`Record ${type} transactions in the business workspace.`} actionLabel="Open business" actionHref="/business" />;
}

function Metric({ label, amount, currency }: { label: string; amount: string; currency: string }) {
  return <div className="border border-line bg-surface p-4"><p className="text-xs uppercase tracking-wide text-muted">{label}</p><p className="mt-2 text-xl"><MoneyAmount amount={amount} currency={currency} /></p></div>;
}