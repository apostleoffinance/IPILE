import { MoneyAmount } from "@/components/financial/MoneyAmount";
import type { Account } from "@/lib/api";
import { cn } from "@/lib/utils";

export function AccountSummary({
  account,
  className,
}: {
  account: Account;
  className?: string;
}) {
  return (
    <article className={cn("border border-line bg-surface px-4 py-4", className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink">{account.name}</p>
          <p className="mt-1 text-xs capitalize text-muted">
            {account.type}
            {account.is_protected ? " · protected" : ""}
            {account.institution ? ` · ${account.institution}` : ""}
          </p>
        </div>
        <p className="text-lg">
          <MoneyAmount amount={account.current_balance} currency={account.currency} />
        </p>
      </div>
    </article>
  );
}
