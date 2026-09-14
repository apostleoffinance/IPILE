"use client";

import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/shared/AppShell";
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { TransactionFilters } from "@/components/transactions/TransactionFilters";
import { TransactionForm, type TransactionDraft } from "@/components/transactions/TransactionForm";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { api, type Account, type Category, type Member, type Transaction } from "@/lib/api";

export default function TransactionsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [type, setType] = useState("");
  const [accountId, setAccountId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [voidId, setVoidId] = useState<string | null>(null);

  async function refresh() {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (accountId) params.set("account_id", accountId);
    const query = params.toString() ? `?${params.toString()}` : "";
    const [nextAccounts, nextCategories, nextMembers, nextTransactions] = await Promise.all([
      api.accounts(),
      api.categories(),
      api.members(),
      api.transactions(query),
    ]);
    setAccounts(nextAccounts);
    setCategories(nextCategories);
    setMembers(nextMembers);
    setTransactions(nextTransactions);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [type, accountId]);

  const filteredCategories = useMemo(
    () => categories.filter((category) => category.kind !== "system"),
    [categories],
  );

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
      <div className="space-y-6 pb-16">
        <div>
          <p className="text-sm text-muted">What moved?</p>
          <h1 className="mt-1 text-3xl font-medium">Transactions</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {accounts.length === 0 ? (
          <EmptyState
            title="Let's find your money"
            body="Add your first bank, cash, or savings account so IPÌLẸ̀ can calculate your household's real financial position."
            actionLabel="+ Add account"
            actionHref="/money/accounts"
          />
        ) : (
          <TransactionForm
            accounts={accounts}
            categories={filteredCategories}
            members={members}
            onSubmit={onSubmit}
            pending={pending}
          />
        )}
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
          <TransactionTable transactions={transactions} accounts={accounts} onVoid={setVoidId} />
        )}
      </div>
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
