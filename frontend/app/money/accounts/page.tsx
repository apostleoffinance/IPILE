"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
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
      <div className="space-y-6 pb-16">
        <div>
          <p className="text-sm text-muted">Where does cash live?</p>
          <h1 className="mt-1 text-3xl font-medium">Accounts</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        <form onSubmit={onSubmit} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            Name
            <input
              required
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Type
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={type}
              onChange={(event) => setType(event.target.value)}
            >
              <option value="bank">Bank</option>
              <option value="savings">Savings</option>
              <option value="cash">Cash</option>
              <option value="wallet">Wallet</option>
              <option value="investment">Investment</option>
              <option value="business">Business</option>
              <option value="credit">Credit</option>
            </select>
          </label>
          <label className="block text-sm">
            Institution
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={institution}
              onChange={(event) => setInstitution(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Opening balance
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
              value={opening}
              onChange={(event) => setOpening(event.target.value)}
            />
          </label>
          <label className="flex items-center gap-2 text-sm md:col-span-2">
            <input
              type="checkbox"
              checked={protectedAccount}
              onChange={(event) => setProtectedAccount(event.target.checked)}
            />
            Protected (excluded from later Safe to Spend)
          </label>
          <div>
            <button type="submit" className="rounded-md bg-accent px-4 py-2 text-sm text-white">
              Add account
            </button>
          </div>
        </form>
        {accounts.length === 0 ? (
          <EmptyState
            title="Let's find your money"
            body="Add your first bank, cash, or savings account so IPÌLẸ̀ can calculate your household's real position."
            actionLabel="+ Add account"
            actionHref="/money/accounts"
          />
        ) : (
          <div className="overflow-x-auto rounded-md border border-line bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Account</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 text-right font-medium">Balance</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">
                      {account.name}
                      {account.is_protected ? <span className="ml-2 text-xs text-muted">protected</span> : null}
                    </td>
                    <td className="px-4 py-3 capitalize">{account.type}</td>
                    <td className="px-4 py-3 text-right">
                      <MoneyAmount amount={account.current_balance} currency={account.currency} />
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
