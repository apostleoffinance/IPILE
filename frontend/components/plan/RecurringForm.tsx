import { FormEvent, useState } from "react";
import { CategorySelector } from "@/components/transactions/CategorySelector";
import type { Account, Category, Member } from "@/lib/api";

export type RecurringDraft = {
  account_id: string;
  amount: string;
  type: string;
  frequency: string;
  next_date: string;
  category_id?: string;
  member_id?: string;
  counterparty_account_id?: string;
  description?: string;
};

export function RecurringForm({
  accounts,
  categories,
  members,
  onSubmit,
  pending,
}: {
  accounts: Account[];
  categories: Category[];
  members: Member[];
  onSubmit: (draft: RecurringDraft) => Promise<void>;
  pending: boolean;
}) {
  const [type, setType] = useState("expense");
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? "");
  const [counterpartyId, setCounterpartyId] = useState("");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState("monthly");
  const [nextDate, setNextDate] = useState(new Date().toISOString().slice(0, 10));
  const [categoryId, setCategoryId] = useState("");
  const [memberId, setMemberId] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await onSubmit({
      account_id: accountId,
      amount,
      type,
      frequency,
      next_date: nextDate,
      category_id: categoryId || undefined,
      member_id: memberId || undefined,
      counterparty_account_id: type === "transfer" ? counterpartyId : undefined,
      description: description || undefined,
    });
    setAmount("");
    setDescription("");
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
      <label className="block text-sm">
        Type
        <select
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={type}
          onChange={(event) => setType(event.target.value)}
        >
          <option value="expense">Expense</option>
          <option value="income">Income</option>
          <option value="giving">Giving</option>
          <option value="transfer">Transfer</option>
        </select>
      </label>
      <label className="block text-sm">
        Amount
        <input
          required
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2 tabular"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          placeholder="40000.00"
        />
      </label>
      <label className="block text-sm">
        Account
        <select
          required
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={accountId}
          onChange={(event) => setAccountId(event.target.value)}
        >
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
      </label>
      {type === "transfer" ? (
        <label className="block text-sm">
          To account
          <select
            required
            className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
            value={counterpartyId}
            onChange={(event) => setCounterpartyId(event.target.value)}
          >
            <option value="">Select account</option>
            {accounts
              .filter((account) => account.id !== accountId)
              .map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
          </select>
        </label>
      ) : (
        <label className="block text-sm">
          Category
          <CategorySelector categories={categories} value={categoryId} onChange={setCategoryId} />
        </label>
      )}
      <label className="block text-sm">
        Frequency
        <select
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={frequency}
          onChange={(event) => setFrequency(event.target.value)}
        >
          <option value="weekly">Weekly</option>
          <option value="biweekly">Every two weeks</option>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="annual">Annual</option>
        </select>
      </label>
      <label className="block text-sm">
        Next date
        <input
          type="date"
          required
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={nextDate}
          onChange={(event) => setNextDate(event.target.value)}
        />
      </label>
      <label className="block text-sm">
        Member
        <select
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={memberId}
          onChange={(event) => setMemberId(event.target.value)}
        >
          <option value="">Household</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.display_name}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        Description
        <input
          className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </label>
      <div className="md:col-span-2">
        <button
          type="submit"
          disabled={pending || !accountId}
          className="rounded-md bg-accent px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          {pending ? "Saving…" : "Add recurring"}
        </button>
      </div>
    </form>
  );
}
