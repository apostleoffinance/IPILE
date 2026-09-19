import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { moneySign } from "@/lib/money-change";
import { cn } from "@/lib/utils";

export function MoneyChange({
  amount,
  currency = "NGN",
  className,
}: {
  amount: string;
  currency?: string;
  className?: string;
}) {
  const sign = moneySign(amount);
  return (
    <span
      className={cn(
        "tabular",
        sign === "positive" && "text-healthy",
        sign === "negative" && "text-critical",
        sign === "neutral" && "text-muted",
        className,
      )}
    >
      {sign === "positive" ? "+" : ""}
      <MoneyAmount amount={amount} currency={currency} />
    </span>
  );
}
