"use client";

import { FormEvent, useEffect, useState } from "react";
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
import { GoalProgress } from "@/components/wealth/GoalProgress";
import {
  contributeToGoal,
  createGoal,
  getAccounts,
  getGoals,
  type Account,
  type HouseholdGoal,
} from "@/lib/api";

export default function GoalsPage() {
  const [rows, setRows] = useState<HouseholdGoal[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("purchase");
  const [target, setTarget] = useState("");
  const [current, setCurrent] = useState("");
  const [deadline, setDeadline] = useState("");
  const [goalId, setGoalId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    const [nextRows, nextAccounts] = await Promise.all([getGoals(), getAccounts()]);
    setRows(nextRows);
    setAccounts(nextAccounts);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    const open = nextRows.find((row) => row.status !== "completed" && row.status !== "cancelled");
    if (!goalId && open) setGoalId(open.id);
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
      await createGoal({
        name,
        type,
        target_amount: target,
        current_amount: current || "0.00",
        deadline: deadline || undefined,
      });
      setName("");
      setTarget("");
      setCurrent("");
      setDeadline("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add goal.");
    } finally {
      setPending(false);
    }
  }

  async function onContribute(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await contributeToGoal(goalId, { account_id: accountId, amount });
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record contribution.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader eyebrow="Wealth" title="Goals" description="Are we getting closer?" />
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}
        <SectionHeader title="Progress" />
        {!rows.length && loaded ? (
          <EmptyState title="No goals yet" body="Name a target, a deadline, and fund it from an account." />
        ) : (
          <div className="space-y-4">
            {rows.map((row) => (
              <GoalProgress
                key={row.id}
                name={row.name}
                type={row.type}
                current={row.current_amount}
                target={row.target_amount}
                percent={row.percent}
                deadline={row.deadline}
                requiredMonthly={row.required_monthly}
                status={row.status}
              />
            ))}
          </div>
        )}
        <form onSubmit={onCreate} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-3">
          <Input
            placeholder="Goal name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
          <Select
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            <option value="education">Education</option>
            <option value="housing">Housing</option>
            <option value="relocation">Relocation</option>
            <option value="purchase">Purchase</option>
            <option value="retirement">Retirement</option>
            <option value="business">Business</option>
            <option value="emergency">Emergency</option>
            <option value="other">Other</option>
          </Select>
          <Input
            placeholder="Target amount"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            required
          />
          <Input
            placeholder="Current amount"
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
          <Input
            type="date"
            className="rounded-md border border-line bg-canvas px-3 py-2"
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
          />
          <Button type="submit" disabled={pending}>
            Add goal
          </Button>
        </form>
        {rows.some((row) => row.status !== "completed" && row.status !== "cancelled") ? (
          <form onSubmit={onContribute} className="grid gap-3 rounded-md border border-line bg-surface p-5 md:grid-cols-4">
            <Select
              value={goalId}
              onChange={(event) => setGoalId(event.target.value)}
            >
              {rows
                .filter((row) => row.status !== "completed" && row.status !== "cancelled")
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
              placeholder="Contribution amount"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              required
            />
            <Button type="submit" disabled={pending}>
              Contribute
            </Button>
          </form>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}
