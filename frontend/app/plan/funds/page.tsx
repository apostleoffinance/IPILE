"use client";

import { FormEvent, useEffect, useState } from "react";
import { FundProgress } from "@/components/plan/FundProgress";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
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
      <ContentContainer>
        <PageHeader eyebrow="Plan" title="Funds" description="Are reserves building on time?" />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        <SectionHeader title="Create fund" />
        <form onSubmit={onCreate} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            Name
            <Input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Target
            <Input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Monthly contribution
            <Input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={monthly}
              onChange={(event) => setMonthly(event.target.value)}
              placeholder="150000.00"
            />
          </label>
          <label className="block text-sm">
            Target date
            <Input
              type="date"
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
            />
          </label>
          <label className="block text-sm md:col-span-2">
            Linked obligation
            <Select
              className="mt-1"
              value={obligationId}
              onChange={(event) => setObligationId(event.target.value)}
            >
              <option value="">None</option>
              {obligations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </label>
          <div>
            <Button type="submit" disabled={pending}>
              Add fund
            </Button>
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
                  <Select
                    className="mt-1 block"
                    value={accountId}
                    onChange={(event) => setAccountId(event.target.value)}
                  >
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </Select>
                </label>
                <label className="block text-sm">
                  Amount
                  <Input
                    required
                    className="mt-1 block rounded-md border border-line bg-canvas px-3 py-2 tabular"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                  />
                </label>
                <Button type="submit">
                  Contribute
                </Button>
              </form>
            </div>
          ))
        )}
      </ContentContainer>
    </AppShell>
  );
}
