"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { DebtSummaryCard } from "@/components/financial/Summaries";
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
  createLiability,
  getAccounts,
  getDebtStrategies,
  getLiabilities,
  payLiability,
  type Account,
  type DebtStrategies,
  type HouseholdLiability,
} from "@/lib/api";

export default function DebtsPage() {
  const [rows, setRows] = useState<HouseholdLiability[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [strategies, setStrategies] = useState<DebtStrategies | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("loan");
  const [balance, setBalance] = useState("");
  const [rate, setRate] = useState("0.12");
  const [minPayment, setMinPayment] = useState("");
  const [extraPayment, setExtraPayment] = useState("0");
  const [payId, setPayId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh(extra = extraPayment) {
    const [nextRows, nextAccounts, nextStrategies] = await Promise.all([
      getLiabilities(),
      getAccounts(),
      getDebtStrategies(extra || "0"),
    ]);
    setRows(nextRows);
    setAccounts(nextAccounts);
    setStrategies(nextStrategies);
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
      await createLiability({
        name,
        type,
        current_balance: balance,
        interest_rate: rate || undefined,
        minimum_payment: minPayment || undefined,
      });
      setName("");
      setBalance("");
      setMinPayment("");
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

  const totalDebt = useMemo(
    () =>
      rows
        .filter((row) => row.status !== "paid_off")
        .reduce((sum, row) => sum + Number(row.current_balance), 0)
        .toFixed(2),
    [rows],
  );
  const openCount = useMemo(() => rows.filter((row) => row.status !== "paid_off").length, [rows]);

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader eyebrow="Wealth" title="Debts" description="Are we getting richer by paying down liabilities?" />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {loaded ? <DebtSummaryCard totalDebt={totalDebt} openCount={openCount} /> : null}
        <SectionHeader title="Liabilities" />
        {!rows.length && loaded ? (
          <EmptyState title="No liabilities" body="Loans and credit appear here. Paid-off debts stay for history." />
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
                    {row.type} · {row.status}
                    {row.interest_rate ? ` · ${(Number(row.interest_rate) * 100).toFixed(1)}% APR` : ""}
                    {row.minimum_payment ? (
                      <>
                        {" · min "}
                        <MoneyAmount amount={row.minimum_payment} />
                      </>
                    ) : null}
                  </p>
                </div>
                <MoneyAmount amount={row.current_balance} />
              </div>
            ))}
          </div>
        )}

        {strategies && strategies.liabilities_considered > 0 ? (
          <section className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-display text-2xl">Payoff strategies</h2>
                <p className="mt-1 text-sm text-muted">
                  Snowball clears smallest balances first. Avalanche attacks the highest rates first.
                </p>
              </div>
              <label className="text-sm">
                Extra monthly payment
                <Input
                  className="ml-2 w-40"
                  value={extraPayment}
                  onChange={(event) => setExtraPayment(event.target.value)}
                  onBlur={() => refresh(extraPayment).catch((err: Error) => setError(err.message))}
                />
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <StrategyCard title="Snowball" strategy={strategies.snowball} currency={strategies.currency} />
              <StrategyCard title="Avalanche" strategy={strategies.avalanche} currency={strategies.currency} />
            </div>
          </section>
        ) : null}

        <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-3">
          <Input
            placeholder="Liability name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Select
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option value="loan">Loan</option>
            <option value="credit">Credit</option>
            <option value="mortgage">Mortgage</option>
            <option value="other">Other</option>
          </Select>
          <Input
            placeholder="Current balance"
            value={balance}
            onChange={(event) => setBalance(event.target.value)}
          />
          <Input
            placeholder="APR (e.g. 0.18)"
            value={rate}
            onChange={(event) => setRate(event.target.value)}
          />
          <Input
            placeholder="Minimum payment"
            value={minPayment}
            onChange={(event) => setMinPayment(event.target.value)}
          />
          <Button type="submit" disabled={pending}>
            Add debt
          </Button>
        </form>
        {rows.some((row) => row.status !== "paid_off") ? (
          <form onSubmit={onPay} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
            <Select
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
              placeholder="Payment amount"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
            <Button type="submit" disabled={pending}>
              Record payment
            </Button>
          </form>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}

function StrategyCard({
  title,
  strategy,
  currency,
}: {
  title: string;
  strategy: DebtStrategies["snowball"];
  currency: string;
}) {
  return (
    <div className="border border-line bg-surface p-5">
      <h3 className="font-display text-xl">{title}</h3>
      <p className="mt-2 text-sm text-muted">
        {strategy.months} months · interest{" "}
        <MoneyAmount amount={strategy.total_interest} currency={currency} />
      </p>
      <ol className="mt-4 list-decimal space-y-1 pl-5 text-sm">
        {strategy.order.map((row) => (
          <li key={row.id}>
            {row.name} · <MoneyAmount amount={row.balance} currency={currency} />
          </li>
        ))}
      </ol>
      {strategy.schedule_summary.length ? (
        <div className="mt-4 space-y-1 text-xs text-muted">
          <p className="uppercase tracking-wide">Schedule summary</p>
          {strategy.schedule_summary.map((row) => (
            <p key={row.month}>
              Month {row.month}: pay <MoneyAmount amount={row.total_payment} currency={currency} /> · remaining{" "}
              <MoneyAmount amount={row.remaining_balance} currency={currency} />
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
