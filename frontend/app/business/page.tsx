"use client";

import { FormEvent, useEffect, useState } from "react";
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
  addBusinessEmployee,
  createBusiness,
  getAccounts,
  getBusinesses,
  postBusinessTx,
  type Account,
  type HouseholdBusiness,
} from "@/lib/api";

export default function BusinessPage() {
  const [rows, setRows] = useState<HouseholdBusiness[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [txType, setTxType] = useState("capital_contribution");
  const [staffName, setStaffName] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextRows, nextAccounts] = await Promise.all([getBusinesses(), getAccounts()]);
    setRows(nextRows);
    setAccounts(nextAccounts.filter((account) => account.type !== "business"));
    if (!accountId && nextAccounts[0]) {
      const household = nextAccounts.find((account) => account.type !== "business");
      if (household) setAccountId(household.id);
    }
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  const salon = rows[0];

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createBusiness({ name, type: "service" });
      setName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add business.");
    } finally {
      setPending(false);
    }
  }

  async function onTx(event: FormEvent) {
    event.preventDefault();
    if (!salon) return;
    setPending(true);
    setError(null);
    try {
      await postBusinessTx(salon.id, {
        type: txType,
        amount,
        date: new Date().toISOString().slice(0, 10),
        account_id:
          txType === "capital_contribution" || txType === "withdrawal" ? accountId : undefined,
      });
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record transaction.");
    } finally {
      setPending(false);
    }
  }

  async function onStaff(event: FormEvent) {
    event.preventDefault();
    if (!salon) return;
    setPending(true);
    setError(null);
    try {
      await addBusinessEmployee(salon.id, { name: staffName, role: "stylist" });
      setStaffName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add employee.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Business"
          title="Businesses"
          description="How much has the family invested? Capital is not lifestyle spend."
        />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        {!rows.length && loaded ? (
          <EmptyState title="No business yet" body="Add a family venture. Capital is not lifestyle spend." />
        ) : null}
        {salon ? (
          <>
            <SectionHeader title={salon.name} description="Has the business generated a return?" />
            <div className="grid gap-3 md:grid-cols-4">
              <Metric label="Family invested" amount={salon.pnl.family_invested} />
              <Metric label="Withdrawn" amount={salon.pnl.family_withdrawn} />
              <Metric label="Equity" amount={salon.pnl.current_business_equity} />
              <Metric label="Return" amount={salon.pnl.family_return} />
              <Metric label="Revenue" amount={salon.pnl.revenue} />
              <Metric label="Expenses" amount={salon.pnl.expenses} />
              <Metric label="Profit" amount={salon.pnl.profit} />
            </div>
            <section>
              <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Employees</h2>
              {!salon.employees.length ? (
                <EmptyState title="No employees" body="Add staff so payroll stays on the business books." />
              ) : (
                <div className="space-y-2">
                  {salon.employees.map((row) => (
                    <div
                      key={row.id}
                      className="flex items-baseline justify-between rounded-md border border-line bg-surface px-4 py-3"
                    >
                      <p className="text-sm">{row.name}</p>
                      <p className="text-xs capitalize text-muted">{row.role}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>
            <section>
              <h2 className="mb-3 text-sm uppercase tracking-wide text-muted">Activity</h2>
              {!salon.transactions.length ? (
                <EmptyState title="No business activity" body="Record capital, revenue, expenses, or withdrawals." />
              ) : (
                <div className="space-y-2">
                  {salon.transactions.map((row) => (
                    <div
                      key={row.id}
                      className="flex items-baseline justify-between rounded-md border border-line bg-surface px-4 py-3"
                    >
                      <p className="text-sm capitalize">{row.type.replaceAll("_", " ")}</p>
                      <MoneyAmount amount={row.amount} />
                    </div>
                  ))}
                </div>
              )}
            </section>
            <form onSubmit={onTx} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
              <Select
                value={txType}
                onChange={(event) => setTxType(event.target.value)}
              >
                <option value="capital_contribution">Capital contribution</option>
                <option value="withdrawal">Withdrawal</option>
                <option value="revenue">Revenue</option>
                <option value="expense">Expense</option>
                <option value="payroll">Payroll</option>
              </Select>
              {(txType === "capital_contribution" || txType === "withdrawal") && (
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
              )}
              <Input
                placeholder="Amount"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
              <Button type="submit" disabled={pending}>
                Record
              </Button>
            </form>
            <form onSubmit={onStaff} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
              <Input
                placeholder="Employee name"
                value={staffName}
                onChange={(event) => setStaffName(event.target.value)}
                required
              />
              <Button type="submit" disabled={pending}>
                Add employee
              </Button>
            </form>
          </>
        ) : null}
        {!salon && loaded ? (
          <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
            <Input
              placeholder="Business name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
            <Button type="submit" disabled={pending}>
              Add business
            </Button>
          </form>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}

function Metric({ label, amount }: { label: string; amount: string }) {
  return (
    <div className="border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-xl">
        <MoneyAmount amount={amount} />
      </p>
    </div>
  );
}
