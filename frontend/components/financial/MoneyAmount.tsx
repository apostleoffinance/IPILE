"use client";

import * as React from "react";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { formatMoneySafe } from "@/lib/money";
import { cn } from "@/lib/utils";

type MoneyAmountProps = {
  amount: string | null | undefined;
  currency?: string;
  className?: string;
};

export function MoneyAmount({ amount, currency, className }: MoneyAmountProps) {
  const householdCurrency = useHouseholdCurrency();
  const displayCurrency = currency ?? householdCurrency ?? "NGN";
  return <span className={cn("tabular", className)}>{formatMoneySafe(amount, displayCurrency)}</span>;
}
