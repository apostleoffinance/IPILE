export type DecisionSeverity = "warning" | "critical" | "neutral" | "info";

export function decisionSeverityClass(severity: DecisionSeverity): string {
  switch (severity) {
    case "warning":
      return "border-warning/40";
    case "critical":
      return "border-critical/40";
    case "info":
      return "border-info/40";
    default:
      return "border-line";
  }
}

export function decisionIconTone(severity: DecisionSeverity): string {
  if (severity === "critical") return "text-critical";
  if (severity === "warning") return "text-warning";
  if (severity === "info") return "text-info";
  return "text-muted";
}

export function obligationCoverageTone(label?: string | null): string {
  if (!label || label === "funded") return "text-healthy";
  if (label.includes("partial") || label.includes("due")) return "text-warning";
  return "text-critical";
}

export function transactionDisplayLabel(tx: {
  description?: string | null;
  merchant?: string | null;
  type: string;
}): string {
  return tx.description || tx.merchant || tx.type;
}

export function sumMoneyStrings(values: string[]): string {
  const total = values.reduce((sum, value) => sum + Number(value), 0);
  if (!Number.isFinite(total)) throw new Error("Invalid money sum");
  return total.toFixed(2);
}

export function safeToSpendReady(components: Record<string, string> | null | undefined): boolean {
  if (!components) return false;
  return Object.values(components).every((value) => /^-?\d+(\.\d{1,2})?$/.test(value.trim()));
}
