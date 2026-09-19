"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { InvestmentSummaryCard } from "@/components/financial/Summaries";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
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
  const [type, setType] = useState("equity");
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
      await createInvestment({ name, type, current_value: value || "0.00" });
      setName("");
      setValue("");
      setType("equity");
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

  const totalValue = useMemo(
    () => rows.reduce((sum, row) => sum + Number(row.current_value), 0).toFixed(2),
    [rows],
  );

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader eyebrow="Wealth" title="Investments" description="Are we getting richer through holdings?" />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {loaded ? <InvestmentSummaryCard totalValue={totalValue} count={rows.length} /> : null}
        <SectionHeader title="Holdings" />
        {!rows.length && loaded ? (
          <EmptyState title="No investments yet" body="Add a holding to track cost basis and current value." />
        ) : (
          <div className="space-y-2">
            {rows.map((row) => (
              <div
                key={row.id}
                className="flex items-baseline justify-between border border-line bg-surface px-4 py-3"
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
        <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
          <Input
            placeholder="Holding name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Select
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option value="equity">Equity</option>
            <option value="fund">Fund</option>
            <option value="bond">Bond</option>
            <option value="treasury">Treasury</option>
            <option value="crypto">Crypto</option>
            <option value="other">Other</option>
          </Select>
          <Input
            placeholder="Current value"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <Button type="submit" disabled={pending}>
            Add investment
          </Button>
        </form>
        {rows.length ? (
          <form onSubmit={onBuy} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
            <Select
              value={buyId}
              onChange={(event) => setBuyId(event.target.value)}
            >
              {rows.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </Select>
            <Select
              value={accountId}
              onChange={(event) => setAccountId(event.target.value)}
            >
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </Select>
            <Input
              placeholder="Buy amount"
              value={buyAmount}
              onChange={(event) => setBuyAmount(event.target.value)}
            />
            <Button type="submit" disabled={pending}>
              Record buy
            </Button>
          </form>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}
