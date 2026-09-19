"use client";

import { FormEvent, useEffect, useState } from "react";
import { AccountSummary } from "@/components/financial/AccountSummary";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select } from "@/components/ui/select";
import { api, type Account } from "@/lib/api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState("bank");
  const [institution, setInstitution] = useState("");
  const [opening, setOpening] = useState("0.00");
  const [protectedAccount, setProtectedAccount] = useState(false);

  async function refresh() {
    setAccounts(await api.accounts());
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createAccount({
        name,
        type,
        institution: institution || undefined,
        current_balance: opening,
        is_protected: protectedAccount,
      });
      setName("");
      setInstitution("");
      setOpening("0.00");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account.");
    }
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Money"
          title="Accounts"
          description="Where does cash live? Protected accounts stay out of Safe to Spend."
        />
        {error ? <ErrorState message={error} /> : null}
        <SectionHeader title="Add account" />
        <form onSubmit={onSubmit} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
          <div>
            <Label htmlFor="acc-name">Name</Label>
            <Input id="acc-name" required className="mt-1" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="acc-type">Type</Label>
            <Select
              id="acc-type"
              className="mt-1 w-full border border-line bg-input px-3 py-2 text-sm"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="bank">Bank</option>
              <option value="savings">Savings</option>
              <option value="cash">Cash</option>
              <option value="wallet">Wallet</option>
              <option value="investment">Investment</option>
              <option value="business">Business</option>
              <option value="credit">Credit</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="acc-institution">Institution</Label>
            <Input
              id="acc-institution"
              className="mt-1"
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="acc-opening">Opening balance</Label>
            <Input
              id="acc-opening"
              className="mt-1 tabular"
              value={opening}
              onChange={(e) => setOpening(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <Checkbox
              type="checkbox"
              checked={protectedAccount}
              onChange={(e) => setProtectedAccount(e.target.checked)}
            />
            Protected (excluded from Safe to Spend)
          </label>
          <div>
            <Button type="submit">Add account</Button>
          </div>
        </form>
        <SectionHeader title="Balances" />
        {accounts.length === 0 ? (
          <EmptyState
            title="Let's find your money"
            body="Add your first bank, cash, or savings account so IPÌLẸ̀ can calculate your household's real position."
            actionLabel="+ Add account"
            actionHref="/money/accounts"
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {accounts.map((account) => (
              <AccountSummary key={account.id} account={account} />
            ))}
          </div>
        )}
      </ContentContainer>
    </AppShell>
  );
}
