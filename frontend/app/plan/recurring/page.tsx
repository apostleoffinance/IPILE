"use client";

import { useEffect, useState } from "react";
import { RecurringForm } from "@/components/plan/RecurringForm";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, type Account, type Category, type Member, type Recurring } from "@/lib/api";

export default function RecurringPage() {
  const [items, setItems] = useState<Recurring[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [nextItems, nextAccounts, nextCategories, nextMembers] = await Promise.all([
      api.recurring(),
      api.accounts(),
      api.categories(),
      api.members(),
    ]);
    setItems(nextItems);
    setAccounts(nextAccounts);
    setCategories(nextCategories);
    setMembers(nextMembers);
    setLoaded(true);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  const accountName = Object.fromEntries(accounts.map((account) => [account.id, account.name]));

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">What repeats?</p>
          <h1 className="mt-1 text-3xl font-medium">Recurring</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {!loaded && !error ? <LoadingState /> : null}

        {accounts.length === 0 ? (
          <EmptyState title="Add an account first" body="Recurring transactions need a household account." />
        ) : (
          <RecurringForm
            accounts={accounts}
            categories={categories.filter((category) => category.kind !== "system")}
            members={members}
            pending={pending}
            onSubmit={async (draft) => {
              setPending(true);
              setError(null);
              try {
                await api.createRecurring(draft);
                await refresh();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Could not save.");
              } finally {
                setPending(false);
              }
            }}
          />
        )}

        {loaded && items.length === 0 ? (
          <EmptyState title="No recurring templates" body="Add a repeating income, expense, or transfer." />
        ) : (
          <div className="overflow-x-auto rounded-md border border-line bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Next</th>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 font-medium">Account</th>
                  <th className="px-4 py-3 font-medium">Amount</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">
                      {item.next_date}
                      <p className="text-xs capitalize text-muted">{item.frequency}</p>
                    </td>
                    <td className="px-4 py-3">
                      {item.description ?? item.merchant ?? item.type}
                    </td>
                    <td className="px-4 py-3">{accountName[item.account_id] ?? "Account"}</td>
                    <td className="px-4 py-3">
                      <MoneyAmount amount={item.amount} currency={item.currency} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        className="text-sm text-accent underline"
                        onClick={async () => {
                          try {
                            await api.postRecurring(item.id);
                            await refresh();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Could not post.");
                          }
                        }}
                      >
                        Post next
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
