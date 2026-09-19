"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { IncomeSummary } from "@/components/financial/NetWorthSummary";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { api, type Account, type IncomeSource, type Transaction } from "@/lib/api";
import { moneyString } from "@/lib/forms";

export default function IncomePage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [sources, setSources] = useState<IncomeSource[]>([]);
  const [income, setIncome] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [accountId, setAccountId] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [sourceName, setSourceName] = useState("");
  const [expected, setExpected] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function refresh() {
    const [nextAccounts, nextSources, nextIncome] = await Promise.all([
      api.accounts(),
      api.incomeSources(),
      api.income(),
    ]);
    setAccounts(nextAccounts);
    setSources(nextSources);
    setIncome(nextIncome);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    if (!sourceId && nextSources[0]) setSourceId(nextSources[0].id);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function recordIncome(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFormError(null);
    if (!moneyString.safeParse(amount).success) {
      setFormError("Enter a valid amount like 150000.00.");
      return;
    }
    try {
      await api.recordIncome({
        account_id: accountId,
        amount,
        date,
        income_source_id: sourceId || undefined,
      });
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record income.");
    }
  }

  async function addSource(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFormError(null);
    if (!moneyString.safeParse(expected).success) {
      setFormError("Enter a valid expected amount like 150000.00.");
      return;
    }
    try {
      await api.createIncomeSource({ name: sourceName, expected_amount: expected });
      setSourceName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create source.");
    }
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader eyebrow="Money" title="Income" description="What is coming in?" />
        {error ? <ErrorState message={error} /> : null}
        {formError ? <p className="text-sm text-critical" role="alert">{formError}</p> : null}

        <SectionHeader title="Sources" />
        {sources.length ? (
          <IncomeSummary sources={sources} />
        ) : (
          <EmptyState title="No income sources" body="Add an expected source so allocation has a baseline." />
        )}

        <form onSubmit={addSource} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-3">
          <div>
            <Label htmlFor="income-source">New source</Label>
            <Input
              id="income-source"
              required
              className="mt-1"
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="income-expected">Expected amount</Label>
            <Input
              id="income-expected"
              required
              className="mt-1 tabular"
              value={expected}
              onChange={(event) => setExpected(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <Button type="submit">Add source</Button>
          </div>
        </form>

        {accounts.length === 0 ? (
          <EmptyState title="Add an account first" body="Income needs a destination account." />
        ) : (
          <>
            <SectionHeader title="Recognize income" />
            <form onSubmit={recordIncome} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
              <div>
                <Label htmlFor="rec-account">Account</Label>
                <Select
                  id="rec-account"
                  className="mt-1"
                  value={accountId}
                  onChange={(event) => setAccountId(event.target.value)}
                >
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="rec-source">Source</Label>
                <Select
                  id="rec-source"
                  className="mt-1"
                  value={sourceId}
                  onChange={(event) => setSourceId(event.target.value)}
                >
                  <option value="">None</option>
                  {sources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="rec-amount">Amount</Label>
                <Input
                  id="rec-amount"
                  required
                  className="mt-1 tabular"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="rec-date">Date</Label>
                <Input
                  id="rec-date"
                  type="date"
                  required
                  className="mt-1"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </div>
              <div className="md:col-span-2">
                <Button type="submit">Recognize income</Button>
              </div>
            </form>
          </>
        )}

        <SectionHeader title="Recognized" />
        {income.length === 0 ? (
          <EmptyState title="No recognized income" body="Record a cleared income transaction for this household." />
        ) : (
          <TransactionTable transactions={income} accounts={accounts} />
        )}
      </ContentContainer>
    </AppShell>
  );
}
