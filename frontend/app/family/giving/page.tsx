"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { GivingSummaryCard } from "@/components/financial/Summaries";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  api,
  type Account,
  type GivingPolicy,
  type GivingSummary,
} from "@/lib/api";

export default function GivingPage() {
  const [summary, setSummary] = useState<GivingSummary | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [policyName, setPolicyName] = useState("");
  const [policyKind, setPolicyKind] = useState("Charity");
  const [monthlyLimit, setMonthlyLimit] = useState("50000.00");
  const [dualApproval, setDualApproval] = useState(false);
  const [amount, setAmount] = useState("10000.00");
  const [accountId, setAccountId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [beneficiary, setBeneficiary] = useState("");

  async function refresh() {
    const [nextSummary, nextAccounts] = await Promise.all([
      api.givingSummary(),
      api.accounts(),
    ]);
    setSummary(nextSummary);
    setAccounts(nextAccounts);
    if (!accountId && nextAccounts[0]) setAccountId(nextAccounts[0].id);
    if (!policyId && nextSummary.policies[0]) setPolicyId(nextSummary.policies[0].id);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onPolicy(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createGivingPolicy({
        name: policyName,
        kind: policyKind,
        monthly_limit: monthlyLimit || undefined,
        requires_dual_approval: dualApproval,
      });
      setPolicyName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save policy.");
    }
  }

  async function onGive(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createGiving({
        kind: policyKind,
        amount,
        account_id: accountId,
        policy_id: policyId || undefined,
        beneficiary: beneficiary || undefined,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record giving.");
    }
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Family"
          title="Giving"
          description="Policies are household configuration, not product rules. Limits warn; they do not invent obligations."
          actions={
            <Link href="/family/members" className="text-sm text-muted underline">
              Members
            </Link>
          }
        />
        {error ? <ErrorState message={error} /> : null}

        {summary ? <GivingSummaryCard summary={summary} /> : null}

        <section className="space-y-3">
          <SectionHeader title="Policies" />
          {summary?.policies.length ? (
            <ul className="space-y-2">
              {summary.policies.map((policy: GivingPolicy) => (
                <li key={policy.id} className="border border-line bg-surface px-4 py-3 text-sm">
                  <p className="font-medium">
                    {policy.name}{" "}
                    {policy.limit_breached ? (
                      <span className="text-xs uppercase tracking-wide text-[var(--color-status-warning)]">
                        Limit
                      </span>
                    ) : null}
                  </p>
                  <p className="mt-1 text-muted">
                    Month <MoneyAmount amount={policy.monthly_used} />
                    {policy.monthly_limit ? (
                      <>
                        {" "}
                        / <MoneyAmount amount={policy.monthly_limit} />
                      </>
                    ) : null}
                    {policy.requires_dual_approval ? " · Dual approval" : null}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No giving policies yet" body="Add a household-defined practice." />
          )}
          <form onSubmit={onPolicy} className="grid gap-3 border border-line bg-surface p-4 md:grid-cols-2">
            <label className="block text-sm">
              Name
              <Input
                className="mt-1 w-full border border-line bg-canvas px-3 py-2"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Kind
              <Input
                className="mt-1 w-full border border-line bg-canvas px-3 py-2"
                value={policyKind}
                onChange={(e) => setPolicyKind(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Monthly limit
              <Input
                className="mt-1 w-full border border-line bg-canvas px-3 py-2"
                value={monthlyLimit}
                onChange={(e) => setMonthlyLimit(e.target.value)}
              />
            </label>
            <label className="flex items-center gap-2 text-sm md:mt-7">
              <Checkbox
                type="checkbox"
                checked={dualApproval}
                onChange={(e) => setDualApproval(e.target.checked)}
              />
              Require dual approval
            </label>
            <Button type="submit" className="md:col-span-2">
              Add policy
            </Button>
          </form>
        </section>

        <section className="space-y-3">
          <h2 className="font-display text-2xl">Record giving</h2>
          <form onSubmit={onGive} className="grid gap-3 border border-line bg-surface p-4 md:grid-cols-2">
            <label className="block text-sm">
              Account
              <Select
                className="mt-1"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                required
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-sm">
              Policy
              <Select
                className="mt-1"
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
              >
                <option value="">None</option>
                {summary?.policies.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.name}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-sm">
              Amount
              <Input
                className="mt-1 w-full border border-line bg-canvas px-3 py-2"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Beneficiary
              <Input
                className="mt-1 w-full border border-line bg-canvas px-3 py-2"
                value={beneficiary}
                onChange={(e) => setBeneficiary(e.target.value)}
              />
            </label>
            <Button type="submit" className="md:col-span-2">
              Record giving
            </Button>
          </form>
        </section>

        {summary?.pending_approvals.length ? (
          <section className="space-y-3">
            <h2 className="font-display text-2xl">Pending approval</h2>
            <ul className="space-y-2">
              {summary.pending_approvals.map((row) => (
                <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 border border-line px-4 py-3 text-sm">
                  <span>
                    {row.kind} · <MoneyAmount amount={row.amount} />
                  </span>
                  <span className="flex gap-2">
                    <Button type="button" variant="link" size="sm"
                      onClick={async () => {
                        await api.approveGiving(row.id);
                        await refresh();
                      }}
                    >
                      Approve
                    </Button>
                    <Button type="button" variant="link" size="sm"
                      onClick={async () => {
                        await api.rejectGiving(row.id);
                        await refresh();
                      }}
                    >
                      Reject
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="space-y-3">
          <h2 className="font-display text-2xl">Recent</h2>
          {summary?.records.length ? (
            <ul className="space-y-2 text-sm">
              {summary.records.map((row) => (
                <li key={row.id} className="border border-line px-4 py-3">
                  <p>
                    {row.date} · {row.kind} · <MoneyAmount amount={row.amount} /> · {row.status}
                  </p>
                  {row.limit_warning ? <p className="mt-1 text-xs text-[var(--color-status-warning)]">{row.limit_warning}</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No giving recorded" body="Post a gift against a policy." />
          )}
        </section>
      </ContentContainer>
    </AppShell>
  );
}

