import type { Account } from "@/lib/api";

export function TransactionFilters({
  accounts,
  type,
  accountId,
  onType,
  onAccount,
}: {
  accounts: Account[];
  type: string;
  accountId: string;
  onType: (value: string) => void;
  onAccount: (value: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <select
        className="rounded-md border border-line bg-surface px-3 py-2 text-sm"
        value={type}
        onChange={(event) => onType(event.target.value)}
      >
        <option value="">All types</option>
        <option value="income">Income</option>
        <option value="expense">Expense</option>
        <option value="transfer">Transfer</option>
        <option value="giving">Giving</option>
      </select>
      <select
        className="rounded-md border border-line bg-surface px-3 py-2 text-sm"
        value={accountId}
        onChange={(event) => onAccount(event.target.value)}
      >
        <option value="">All accounts</option>
        {accounts.map((account) => (
          <option key={account.id} value={account.id}>
            {account.name}
          </option>
        ))}
      </select>
    </div>
  );
}
