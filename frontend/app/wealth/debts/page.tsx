"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  createLiability,
  getAccounts,
  getLiabilities,
  payLiability,
  type Account,
  type HouseholdLiability,
} from "@/lib/api";

export default function DebtsPage() {
  const [rows, setRows] = useState<HouseholdLiability[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("loan");
  const [balance, setBalance] = useState("");
  const [payId, setPayId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextRows, nextAccounts] = await Promise.all([getLiabilities(), getAccounts()]);
    setRows(nextRows);
    setAccounts(nextAccounts);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    const open = nextRows.find((row) => row.status !== "paid_off");
    if (!payId && open) setPayId(open.id);
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
      await createLiability({ name, type, current_balance: balance });
      setName("");
      setBalance("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add liability.");
    } finally {
      setPending(false);
    }
  }

  async function onPay(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await payLiability(payId, { account_id: accountId, amount });
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record payment.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">Are we getting richer?</p>
          <h1 className="mt-1 text-3xl font-medium">Debts</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {!rows.length && loaded ? (
          <EmptyState title="No liabilities" body="Loans and credit appear here. Paid-off debts stay for history." />
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
                    {row.type} · {row.status}
                  </p>
                </div>
                <MoneyAmount amount={row.current_balance} />
              </div>
            ))}
          </div>
        )}
        <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
          <input
            className="rounded-md border border-line bg-canvas px-3 py-2"
            placeholder="Liability name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <select
            className="rounded-md border border-line bg-canvas px-3 py-2"
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option value="loan">Loan</option>
            <option value="credit">Credit</option>
            <option value="mortgage">Mortgage</option>
            <option value="other">Other</option>
          </select>
          <input
            className="rounded-md border border-line bg-canvas px-3 py-2"
            placeholder="Current balance"
            value={balance}
            onChange={(event) => setBalance(event.target.value)}
          />
          <button type="submit" disabled={pending} className="rounded-md bg-ink px-4 py-2 text-canvas">
            Add debt
          </button>
        </form>
        {rows.some((row) => row.status !== "paid_off") ? (
          <form onSubmit={onPay} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
            <select
              className="rounded-md border border-line bg-canvas px-3 py-2"
              value={payId}
              onChange={(event) => setPayId(event.target.value)}
            >
              {rows
                .filter((row) => row.status !== "paid_off")
                .map((row) => (
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
              placeholder="Payment amount"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
            <button type="submit" disabled={pending} className="rounded-md bg-ink px-4 py-2 text-canvas">
              Record payment
            </button>
          </form>
        ) : null}
      </div>
    </AppShell>
  );
}
