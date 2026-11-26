"use client";

import * as React from "react";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { formatMoney } from "@/lib/money";
import { cn } from "@/lib/utils";

type MoneyAmountProps = {
  amount: string;
  currency?: string;
  className?: string;
};

export function MoneyAmount({ amount, currency, className }: MoneyAmountProps) {
  const householdCurrency = useHouseholdCurrency();
  const displayCurrency = currency ?? householdCurrency ?? "NGN";
  return <span className={cn("tabular", className)}>{formatMoney(amount, displayCurrency)}</span>;
}
