import { parseMoney } from "./money";

export type MoneySign = "positive" | "negative" | "neutral";

export function moneySign(amount: string): MoneySign {
  const normalized = parseMoney(amount);
  if (normalized === "0.00" || normalized === "-0.00") return "neutral";
  return normalized.startsWith("-") ? "negative" : "positive";
}

/** Returns `after - before` as a decimal money string. */
export function moneyDelta(after: string, before: string): string {
  const a = Number(parseMoney(after));
  const b = Number(parseMoney(before));
  return (a - b).toFixed(2);
}
