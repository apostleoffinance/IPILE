import { MoneyAmount } from "@/components/financial/MoneyAmount";
import type { Transaction } from "@/lib/api";
import { cn } from "@/lib/utils";

export function TransactionRow({
  transaction,
  accountName,
  onVoid,
  className,
}: {
  transaction: Transaction;
  accountName?: string;
  onVoid?: (id: string) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-baseline justify-between gap-4 border border-line bg-surface px-4 py-3 text-sm",
        className,
      )}
    >
      <div className="min-w-0">
        <p className="truncate font-medium text-ink">
          {transaction.description || transaction.merchant || transaction.type}
        </p>
        <p className="mt-1 text-xs capitalize text-muted">
          {transaction.date} · {transaction.type.replaceAll("_", " ")}
          {accountName ? ` · ${accountName}` : ""}
          {transaction.status !== "posted" ? ` · ${transaction.status}` : ""}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <MoneyAmount amount={transaction.amount} currency={transaction.currency} />
        {onVoid && transaction.status !== "voided" ? (
          <button type="button" className="text-xs text-muted underline" onClick={() => onVoid(transaction.id)}>
            Void
          </button>
        ) : null}
      </div>
    </div>
  );
}
