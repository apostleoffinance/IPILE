export function decisionHrefForPattern(code: string): string {
  const lower = code.toLowerCase();
  if (lower.includes("giving")) return "/family/giving";
  if (lower.includes("budget") || lower.includes("overspend")) return "/plan/budget";
  if (lower.includes("obligation") || lower.includes("due")) return "/plan/obligations";
  if (lower.includes("debt")) return "/wealth/debts";
  if (lower.includes("goal")) return "/wealth/goals";
  if (lower.includes("income")) return "/money/income";
  if (lower.includes("account") || lower.includes("cash")) return "/money/accounts";
  return "/insights";
}
