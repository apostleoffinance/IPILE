import { formatNaira } from "@/lib/money";

type MoneyAmountProps = {
  amount: string;
  currency?: string;
  className?: string;
};

export function MoneyAmount({ amount, currency = "NGN", className }: MoneyAmountProps) {
  return <span className={`tabular ${className ?? ""}`}>{formatNaira(amount, currency)}</span>;
}
