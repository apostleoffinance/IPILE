"use client";

import { useEffect, useMemo, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { TransactionFilters } from "@/components/transactions/TransactionFilters";
import { TransactionForm, type TransactionDraft } from "@/components/transactions/TransactionForm";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api, type Account, type Category, type Member, type Transaction } from "@/lib/api";

export default function TransactionsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [currentMember, setCurrentMember] = useState<Member | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [type, setType] = useState("");
  const [accountId, setAccountId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [voidId, setVoidId] = useState<string | null>(null);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [editDate, setEditDate] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editMerchant, setEditMerchant] = useState("");
  const [editCategoryId, setEditCategoryId] = useState("");
  const [editMemberId, setEditMemberId] = useState("");

  async function refresh() {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (accountId) params.set("account_id", accountId);
    const query = params.toString() ? `?${params.toString()}` : "";
    const [nextAccounts, nextCategories, nextMembers, me, nextTransactions] = await Promise.all([
      api.accounts(),
      api.categories(),
      api.members(),
      api.currentMember(),
      api.transactions(query),
    ]);
    setAccounts(nextAccounts);
    setCategories(nextCategories);
    setCurrentMember(me);
    setMembers(me.role === "member" ? nextMembers.filter((member) => member.id === me.id) : nextMembers);
    setTransactions(nextTransactions);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [type, accountId]);

  const filteredCategories = useMemo(
    () => categories.filter((category) => category.kind !== "system"),
    [categories],
  );

  function startEdit(transaction: Transaction) {
    setEditingTransaction(transaction);
    setEditDate(transaction.date);
    setEditDescription(transaction.description ?? "");
    setEditMerchant(transaction.merchant ?? "");
    setEditCategoryId(transaction.category_id ?? "");
    setEditMemberId(transaction.member_id ?? "");
  }

  async function onUpdateTransaction(event: React.FormEvent) {
    event.preventDefault();
    if (!editingTransaction) return;
    setPending(true);
    setError(null);
    try {
      await api.updateTransaction(editingTransaction.id, {
        date: editDate,
        description: editDescription || null,
        merchant: editMerchant || null,
        category_id: editCategoryId || null,
        member_id: editMemberId || null,
      });
      setEditingTransaction(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update transaction.");
    } finally {
      setPending(false);
    }
  }

  async function onSubmit(draft: TransactionDraft) {
    setPending(true);
    setError(null);
    try {
      await api.createTransaction(draft);
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
        <PageHeader
          eyebrow="Money"
          title="Transactions"
          description="What moved? Record income, spending, transfers, and giving."
        />
        {error ? <ErrorState message={error} /> : null}
        {accounts.length === 0 ? (
          <EmptyState
            title="Let's find your money"
            body="Add your first bank, cash, or savings account so IPÌLẸ̀ can calculate your household's real financial position."
            actionLabel="+ Add account"
            actionHref="/money/accounts"
          />
        ) : currentMember && ["owner", "partner", "member"].includes(currentMember.role) ? (
          <>
            <SectionHeader title="Record" description="Validated before it hits balances." />
            <TransactionForm
              accounts={accounts}
              categories={filteredCategories}
              members={members}
              onSubmit={onSubmit}
              pending={pending}
            />
          </>
        ) : null}
        {editingTransaction ? (
          <form onSubmit={onUpdateTransaction} className="mb-5 grid gap-3 border border-line bg-surface p-4 md:grid-cols-2">
            <div className="md:col-span-2 font-semibold">Edit transaction</div>
            <div>
              <Label htmlFor="edit-tx-date">Date</Label>
              <Input id="edit-tx-date" className="mt-1" type="date" value={editDate} onChange={(event) => setEditDate(event.target.value)} required />
            </div>
            <div>
              <Label htmlFor="edit-tx-merchant">Merchant</Label>
              <Input id="edit-tx-merchant" className="mt-1" value={editMerchant} onChange={(event) => setEditMerchant(event.target.value)} />
            </div>
            <div>
              <Label htmlFor="edit-tx-description">Description</Label>
              <Input id="edit-tx-description" className="mt-1" value={editDescription} onChange={(event) => setEditDescription(event.target.value)} />
            </div>
            <div>
              <Label htmlFor="edit-tx-category">Category</Label>
              <Select id="edit-tx-category" className="mt-1" value={editCategoryId} onChange={(event) => setEditCategoryId(event.target.value)}>
                <option value="">No category</option>
                {filteredCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </Select>
            </div>
            {currentMember && ["owner", "partner"].includes(currentMember.role) ? (
              <div>
                <Label htmlFor="edit-tx-member">Member attribution</Label>
                <Select id="edit-tx-member" className="mt-1" value={editMemberId} onChange={(event) => setEditMemberId(event.target.value)}>
                  <option value="">Household</option>
                  {members.map((member) => <option key={member.id} value={member.id}>{member.display_name}</option>)}
                </Select>
              </div>
            ) : null}
            <div className="flex items-end gap-2">
              <Button type="submit" disabled={pending}>Save changes</Button>
              <Button type="button" variant="ghost" onClick={() => setEditingTransaction(null)}>Cancel</Button>
            </div>
          </form>
        ) : null}
        <SectionHeader title="Activity" />
        <TransactionFilters
          accounts={accounts}
          type={type}
          accountId={accountId}
          onType={setType}
          onAccount={setAccountId}
        />
        {transactions.length === 0 ? (
          <EmptyState title="No transactions" body="Record income, spending, or a transfer." />
        ) : (
          <TransactionTable
            transactions={transactions}
            accounts={accounts}
            onVoid={currentMember && ["owner", "partner"].includes(currentMember.role) ? setVoidId : undefined}
            onEdit={currentMember && ["owner", "partner", "member"].includes(currentMember.role) ? startEdit : undefined}
            canEdit={(transaction) =>
              !currentMember ||
              ["owner", "partner"].includes(currentMember.role) ||
              (currentMember.role === "member" && transaction.member_id === currentMember.id)
            }
          />
        )}
      </ContentContainer>
      {voidId ? (
        <ConfirmationDialog
          title="Void this transaction?"
          body="Balances will reverse. The row stays as voided."
          confirmLabel="Void"
          onClose={() => setVoidId(null)}
          onConfirm={async () => {
            try {
              await api.voidTransaction(voidId);
              setVoidId(null);
              await refresh();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Could not void.");
            }
          }}
        />
      ) : null}
    </AppShell>
  );
}
