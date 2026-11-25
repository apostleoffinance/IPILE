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
import { api, type Account, type Member } from "@/lib/api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [currentMember, setCurrentMember] = useState<Member | null>(null);
  const [accessScope, setAccessScope] = useState<"shared" | "personal">("shared");
  const [ownerMemberId, setOwnerMemberId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState("bank");
  const [institution, setInstitution] = useState("");
  const [opening, setOpening] = useState("0.00");
  const [protectedAccount, setProtectedAccount] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editInstitution, setEditInstitution] = useState("");
  const [editProtected, setEditProtected] = useState(false);
  const [editEmergency, setEditEmergency] = useState(false);
  const [editSafeToSpend, setEditSafeToSpend] = useState(true);
  const [editNetWorth, setEditNetWorth] = useState(true);

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

  function startEdit(account: Account) {
    setEditingId(account.id);
    setEditName(account.name);
    setEditInstitution(account.institution ?? "");
    setEditProtected(account.is_protected);
    setEditEmergency(account.is_emergency);
    setEditSafeToSpend(account.include_in_safe_to_spend);
    setEditNetWorth(account.include_in_net_worth);
  }

  async function onUpdateAccount(event: FormEvent) {
    event.preventDefault();
    if (!editingId) return;
    setError(null);
    try {
      await api.updateAccount(editingId, {
        name: editName,
        institution: editInstitution || null,
        ...(currentMember && ["owner", "partner"].includes(currentMember.role)
          ? {
              is_protected: editProtected,
              is_emergency: editEmergency,
              include_in_safe_to_spend: editSafeToSpend,
              include_in_net_worth: editNetWorth,
            }
          : {}),
      });
      setEditingId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update account.");
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.createAccount({
        name,
        type,
        institution: institution || undefined,
        current_balance: opening,
        ...(currentMember && ["owner", "partner"].includes(currentMember.role)
          ? { is_protected: protectedAccount }
          : {}),
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
          {currentMember && ["owner", "partner"].includes(currentMember.role) ? (
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <Checkbox
                type="checkbox"
                checked={protectedAccount}
                onChange={(e) => setProtectedAccount(e.target.checked)}
              />
              Protected (excluded from Safe to Spend)
            </label>
          ) : null}
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
            {accounts.map((account) => {
              const canEdit =
                currentMember &&
                (["owner", "partner"].includes(currentMember.role) ||
                  (currentMember.role === "member" &&
                    account.access_scope === "personal" &&
                    account.owner_member_id === currentMember.id));
              return (
                <div key={account.id} className="space-y-3">
                  <div className="mb-1 flex items-center justify-between text-xs text-muted">
                    <span>{account.access_scope === "personal" ? "Personal account" : "Shared household account"}</span>
                    {account.owner_member_id ? (
                      <span>{members.find((member) => member.id === account.owner_member_id)?.display_name ?? "Personal owner"}</span>
                    ) : null}
                  </div>
                  <AccountSummary account={account} />
                  {canEdit ? (
                    <div className="flex justify-end">
                      <Button type="button" variant="outline" size="sm" onClick={() => startEdit(account)}>
                        Edit account
                      </Button>
                    </div>
                  ) : null}
                  {editingId === account.id ? (
                    <form onSubmit={onUpdateAccount} className="grid gap-3 border border-line bg-surface p-4">
                      <div>
                        <Label htmlFor={`edit-account-name-${account.id}`}>Account name</Label>
                        <Input id={`edit-account-name-${account.id}`} className="mt-1" value={editName} onChange={(event) => setEditName(event.target.value)} required />
                      </div>
                      <div>
                        <Label htmlFor={`edit-account-institution-${account.id}`}>Institution</Label>
                        <Input id={`edit-account-institution-${account.id}`} className="mt-1" value={editInstitution} onChange={(event) => setEditInstitution(event.target.value)} />
                      </div>
                      {currentMember && ["owner", "partner"].includes(currentMember.role) ? (
                        <>
                          <label className="flex items-center gap-2 text-sm">
                            <Checkbox checked={editProtected} onChange={(event) => setEditProtected(event.target.checked)} />
                            Protected from Safe to Spend
                          </label>
                          <label className="flex items-center gap-2 text-sm">
                            <Checkbox checked={editEmergency} onChange={(event) => setEditEmergency(event.target.checked)} />
                            Emergency account
                          </label>
                          <label className="flex items-center gap-2 text-sm">
                            <Checkbox checked={editSafeToSpend} onChange={(event) => setEditSafeToSpend(event.target.checked)} />
                            Include in Safe to Spend
                          </label>
                          <label className="flex items-center gap-2 text-sm">
                            <Checkbox checked={editNetWorth} onChange={(event) => setEditNetWorth(event.target.checked)} />
                            Include in net worth
                          </label>
                        </>
                      ) : null}
                      <div className="flex gap-2">
                        <Button type="submit">Save changes</Button>
                        <Button type="button" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                      </div>
                    </form>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </ContentContainer>
    </AppShell>
  );
}
