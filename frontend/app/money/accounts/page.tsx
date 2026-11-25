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
  const [members, setMembers] = useState<import("@/lib/api").Member[]>([]);
  const [currentMember, setCurrentMember] = useState<import("@/lib/api").Member | null>(null);
  const [accessScope, setAccessScope] = useState<"shared" | "personal">("shared");
  const [ownerMemberId, setOwnerMemberId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState("bank");
  const [institution, setInstitution] = useState("");
  const [opening, setOpening] = useState("0.00");
  const [protectedAccount, setProtectedAccount] = useState(false);

  async function refresh() {
    const [accountRows, memberRows, me] = await Promise.all([
      api.accounts(),
      api.members(),
      api.currentMember(),
    ]);
    setAccounts(accountRows);
    setMembers(memberRows);
    setCurrentMember(me);
    if (me.role === "member") {
      setAccessScope("personal");
      setOwnerMemberId(me.id);
    } else if (!ownerMemberId && memberRows[0]) {
      setOwnerMemberId(memberRows[0].id);
    }
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
        access_scope: currentMember?.role === "member" ? "personal" : accessScope,
        ...(currentMember?.role === "member"
          ? { owner_member_id: currentMember.id }
          : accessScope === "personal"
            ? { owner_member_id: ownerMemberId }
            : {}),
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
        {currentMember && ["owner", "partner", "member"].includes(currentMember.role) ? (
        <>
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
          {currentMember.role !== "member" ? (
            <div>
              <Label htmlFor="acc-scope">Visibility</Label>
              <Select
                id="acc-scope"
                className="mt-1"
                value={accessScope}
                onChange={(e) => setAccessScope(e.target.value as "shared" | "personal")}
              >
                <option value="shared">Shared household account</option>
                <option value="personal">Personal account</option>
              </Select>
            </div>
          ) : (
            <p className="text-sm text-muted">This account will be personal and visible only to you and authorized household administrators.</p>
          )}
          {currentMember.role !== "member" && accessScope === "personal" ? (
            <div>
              <Label htmlFor="acc-owner">Account owner</Label>
              <Select id="acc-owner" className="mt-1" value={ownerMemberId} onChange={(e) => setOwnerMemberId(e.target.value)} required>
                {members.map((member) => <option key={member.id} value={member.id}>{member.display_name}</option>)}
              </Select>
            </div>
          ) : null}
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
        </>
        ) : null}
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
