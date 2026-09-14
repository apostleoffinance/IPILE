"use client";

import { FormEvent, useEffect, useState } from "react";
import { FundProgress } from "@/components/plan/FundProgress";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, type Account, type Fund, type Obligation } from "@/lib/api";

export default function FundsPage() {
  const [funds, setFunds] = useState<Fund[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [monthly, setMonthly] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [obligationId, setObligationId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextFunds, nextAccounts, nextObligations] = await Promise.all([
      api.funds(),
      api.accounts(),
      api.obligations(),
    ]);
    setFunds(nextFunds);
    setAccounts(nextAccounts);
    setObligations(nextObligations);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
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
      await api.createFund({
        name,
        target_amount: target,
        monthly_contribution: monthly || "0.00",
        target_date: targetDate || undefined,
        obligation_id: obligationId || undefined,
      });
      setName("");
      setTarget("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">Are reserves building on time?</p>
          <h1 className="mt-1 text-3xl font-medium">Funds</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        <form onSubmit={onCreate} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            Name
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Target
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Monthly contribution
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={monthly}
              onChange={(event) => setMonthly(event.target.value)}
              placeholder="150000.00"
            />
          </label>
          <label className="block text-sm">
            Target date
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
            />
          </label>
          <label className="block text-sm md:col-span-2">
            Linked obligation
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={obligationId}
              onChange={(event) => setObligationId(event.target.value)}
            >
              <option value="">None</option>
              {obligations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <div>
            <button type="submit" disabled={pending} className="rounded-md bg-accent px-4 py-2 text-sm text-white">
              Add fund
            </button>
          </div>
        </form>

        {loaded && funds.length === 0 ? (
          <EmptyState title="No sinking funds" body="Attach a fund to an obligation or create a reserve." />
        ) : (
          funds.map((fund) => (
            <div key={fund.id} className="space-y-3">
              <FundProgress
                name={fund.name}
                current={fund.current_amount}
                target={fund.target_amount}
                progress={fund.progress}
                coverageLabel={fund.coverage_label}
                requiredMonthly={fund.required_monthly}
                onTrack={fund.on_track}
                shortfall={fund.shortfall}
              />
              <form
                className="flex flex-wrap items-end gap-3"
                onSubmit={async (event) => {
                  event.preventDefault();
                  try {
                    await api.contribute(fund.id, { account_id: accountId, amount });
                    setAmount("");
                    await refresh();
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Could not contribute.");
                  }
                }}
              >
                <label className="block text-sm">
                  From account
                  <select
                    className="mt-1 block rounded-md border border-line bg-canvas px-3 py-2"
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
                  Amount
                  <input
                    required
                    className="mt-1 block rounded-md border border-line bg-canvas px-3 py-2 tabular"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                  />
                </label>
                <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm text-white">
                  Contribute
                </button>
              </form>
            </div>
          ))
        )}
      </div>
    </AppShell>
  );
}
