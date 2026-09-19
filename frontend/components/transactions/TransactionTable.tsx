import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { Button } from "@/components/ui/button";
import type { Account, Transaction } from "@/lib/api";
import { transactionDisplayLabel } from "@/lib/financial-kit";

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
    <div className="overflow-x-auto border border-line bg-surface" role="region" aria-label="Transactions">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">
              Date
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Description
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Account
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Type
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Status
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              Amount
            </th>
            {onVoid ? (
              <th scope="col" className="px-4 py-3">
                <span className="sr-only">Actions</span>
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {transactions.map((row) => (
            <tr key={row.id} className="border-b border-line last:border-0">
              <td className="px-4 py-3">{row.date}</td>
              <td className="px-4 py-3">{transactionDisplayLabel(row)}</td>
              <td className="px-4 py-3">{names[row.account_id] ?? "Account"}</td>
              <td className="px-4 py-3 capitalize">{row.type.replaceAll("_", " ")}</td>
              <td className="px-4 py-3 capitalize">{row.status}</td>
              <td className="px-4 py-3 text-right">
                <MoneyAmount amount={row.amount} currency={row.currency} />
              </td>
              {onVoid ? (
                <td className="px-4 py-3 text-right">
                  {row.status !== "voided" ? (
                    <Button type="button" variant="link" className="h-auto p-0 text-xs" onClick={() => onVoid(row.id)}>
                      Void
                    </Button>
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
