"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { api, type Account, type IncomeSource, type Transaction } from "@/lib/api";

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
  const [expected, setExpected] = useState("2000000.00");

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
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">What is coming in?</p>
          <h1 className="mt-1 text-3xl font-medium">Income</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}

        <section className="grid gap-3 md:grid-cols-2">
          {sources.map((source) => (
            <div key={source.id} className="rounded-md border border-line bg-surface p-4">
              <p className="text-sm text-muted">{source.name}</p>
              <p className="mt-2 text-xl">
                <MoneyAmount amount={source.expected_amount} />
              </p>
              <p className="mt-1 text-xs capitalize text-muted">{source.frequency}</p>
            </div>
          ))}
        </section>

        <form onSubmit={addSource} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-3">
          <label className="block text-sm">
            New source
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Expected amount
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={expected}
              onChange={(event) => setExpected(event.target.value)}
            />
          </label>
          <div className="flex items-end">
            <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm text-white">
              Add source
            </button>
          </div>
        </form>

        {accounts.length === 0 ? (
          <EmptyState title="Add an account first" body="Income needs a destination account." />
        ) : (
          <form onSubmit={recordIncome} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
            <label className="block text-sm">
              Account
              <select
                className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
                value={accountId}
                onChange={(event) => setAccountId(event.target.value)}
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Source
              <select
                className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
                value={sourceId}
                onChange={(event) => setSourceId(event.target.value)}
              >
                <option value="">None</option>
                {sources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Amount
              <input
                required
                className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>
            <label className="block text-sm">
              Date
              <input
                type="date"
                required
                className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
                value={date}
                onChange={(event) => setDate(event.target.value)}
              />
            </label>
            <div className="md:col-span-2">
              <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm text-white">
                Recognize income
              </button>
            </div>
          </form>
        )}

        {income.length === 0 ? (
          <EmptyState title="No recognized income" body="Record a cleared income transaction for this household." />
        ) : (
          <TransactionTable transactions={income} accounts={accounts} />
        )}
      </div>
    </AppShell>
  );
}
