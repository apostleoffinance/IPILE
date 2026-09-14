import { MoneyAmount } from "@/components/financial/MoneyAmount";
import type { Account, Transaction } from "@/lib/api";

export function TransactionTable({
  transactions,
  accounts,
  onVoid,
}: {
  transactions: Transaction[];
  accounts: Account[];
  onVoid?: (id: string) => void;
}) {
  const names = Object.fromEntries(accounts.map((account) => [account.id, account.name]));
  return (
    <div className="overflow-x-auto rounded-md border border-line bg-surface">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium">Description</th>
            <th className="px-4 py-3 font-medium">Account</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 text-right font-medium">Amount</th>
            {onVoid ? <th className="px-4 py-3" /> : null}
          </tr>
        </thead>
        <tbody>
          {transactions.map((row) => (
            <tr key={row.id} className="border-b border-line last:border-0">
              <td className="px-4 py-3">{row.date}</td>
              <td className="px-4 py-3">{row.description || row.merchant || "—"}</td>
              <td className="px-4 py-3">{names[row.account_id] ?? "Account"}</td>
              <td className="px-4 py-3 capitalize">{row.type.replaceAll("_", " ")}</td>
              <td className="px-4 py-3 capitalize">{row.status}</td>
              <td className="px-4 py-3 text-right">
                <MoneyAmount amount={row.amount} currency={row.currency} />
              </td>
              {onVoid ? (
                <td className="px-4 py-3 text-right">
                  {row.status !== "voided" ? (
                    <button type="button" className="text-xs text-muted underline" onClick={() => onVoid(row.id)}>
                      Void
                    </button>
                  ) : null}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
