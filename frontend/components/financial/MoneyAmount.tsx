import * as React from "react";
import { formatNaira } from "@/lib/money";
import { cn } from "@/lib/utils";

type MoneyAmountProps = {
  amount: string;
  currency?: string;
  className?: string;
};

export function MoneyAmount({ amount, currency = "NGN", className }: MoneyAmountProps) {
  return <span className={cn("tabular", className)}>{formatNaira(amount, currency)}</span>;
}
