"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  createInvestment,
  getAccounts,
  getInvestments,
  recordInvestmentTx,
  type Account,
  type HouseholdInvestment,
} from "@/lib/api";

export default function InvestmentsPage() {
  const [rows, setRows] = useState<HouseholdInvestment[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [buyId, setBuyId] = useState("");
  const [buyAmount, setBuyAmount] = useState("");
  const [accountId, setAccountId] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextRows, nextAccounts] = await Promise.all([getInvestments(), getAccounts()]);
    setRows(nextRows);
    setAccounts(nextAccounts);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    if (!buyId && nextRows[0]) setBuyId(nextRows[0].id);
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
      await createInvestment({ name, type: "equity", current_value: value || "0.00" });
      setName("");
      setValue("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add investment.");
    } finally {
      setPending(false);
    }
  }

  async function onBuy(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await recordInvestmentTx(buyId, {
        type: "buy",
        amount: buyAmount,
        date: new Date().toISOString().slice(0, 10),
        account_id: accountId || undefined,
      });
      setBuyAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record buy.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">Are we getting richer?</p>
          <h1 className="mt-1 text-3xl font-medium">Investments</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {!rows.length && loaded ? (
          <EmptyState title="No investments yet" body="Add a holding to track cost basis and current value." />
        ) : (
          <div className="space-y-2">
            {rows.map((row) => (
              <div
                key={row.id}
                className="flex items-baseline justify-between rounded-md border border-line bg-surface px-4 py-3"
              >
                <div>
                  <p className="text-sm">{row.name}</p>
                  <p className="mt-1 text-xs capitalize text-muted">
                    {row.type}
                    {row.institution ? ` · ${row.institution}` : ""}
                    {` · cost ${row.cost_basis}`}
                  </p>
                </div>
                <MoneyAmount amount={row.current_value} />
              </div>
            ))}
          </div>
        )}
        <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-3">
          <input
            className="rounded-md border border-line bg-canvas px-3 py-2"
            placeholder="Holding name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <input
            className="rounded-md border border-line bg-canvas px-3 py-2"
            placeholder="Current value"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <button type="submit" disabled={pending} className="rounded-md bg-ink px-4 py-2 text-canvas">
            Add investment
          </button>
        </form>
        {rows.length ? (
          <form onSubmit={onBuy} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
            <select
              className="rounded-md border border-line bg-canvas px-3 py-2"
              value={buyId}
              onChange={(event) => setBuyId(event.target.value)}
            >
              {rows.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
            <select
              className="rounded-md border border-line bg-canvas px-3 py-2"
              value={accountId}
              onChange={(event) => setAccountId(event.target.value)}
            >
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
            <input
              className="rounded-md border border-line bg-canvas px-3 py-2"
              placeholder="Buy amount"
              value={buyAmount}
              onChange={(event) => setBuyAmount(event.target.value)}
            />
            <button type="submit" disabled={pending} className="rounded-md bg-ink px-4 py-2 text-canvas">
              Record buy
            </button>
          </form>
        ) : null}
      </div>
    </AppShell>
  );
}
