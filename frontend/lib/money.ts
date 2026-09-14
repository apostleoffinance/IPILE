export type MoneyString = string;

export function parseMoney(value: string): string {
  const text = value.trim();
  if (!/^-?\d+(\.\d{1,2})?$/.test(text)) {
    throw new Error("Amount must be a decimal string.");
  }
  const [whole, fraction = ""] = text.split(".");
  return `${whole}.${fraction.padEnd(2, "0").slice(0, 2)}`;
}

export function formatNaira(value: string, currency = "NGN"): string {
  const normalized = parseMoney(value);
  const negative = normalized.startsWith("-");
  const absolute = negative ? normalized.slice(1) : normalized;
  const [whole, fraction] = absolute.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const symbol = currency === "NGN" ? "₦" : `${currency} `;
  return `${negative ? "-" : ""}${symbol}${grouped}.${fraction}`;
}
