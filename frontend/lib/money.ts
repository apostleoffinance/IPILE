export type MoneyString = string;

export function parseMoney(value: string): string {
  const text = value.trim();
  if (!/^-?\d+(\.\d{1,2})?$/.test(text)) {
    throw new Error("Amount must be a decimal string.");
  }
  const [whole, fraction = ""] = text.split(".");
  return whole + "." + fraction.padEnd(2, "0").slice(0, 2);
}

const LOCALES: Record<string, string> = {
  NGN: "en-NG", USD: "en-US", GBP: "en-GB", EUR: "de-DE",
  CHF: "de-CH", CAD: "en-CA", AUD: "en-AU", AED: "en-AE",
  GHS: "en-GH", KES: "en-KE", ZAR: "en-ZA", JPY: "ja-JP",
};

export function formatMoney(value: string, currency = "NGN"): string {
  const code = currency.toUpperCase();
  const normalized = parseMoney(value);
  const negative = normalized.startsWith("-");
  const absolute = negative ? normalized.slice(1) : normalized;
  const [whole, fraction = ""] = absolute.split(".");
  const formatter = new Intl.NumberFormat(LOCALES[code] ?? "en", {
    style: "currency",
    currency: code,
    currencyDisplay: "symbol",
  });
  const digits = formatter.resolvedOptions().maximumFractionDigits ?? 2;
  const parts = formatter.formatToParts(0);
  const integerIndex = parts.findIndex((part) => part.type === "integer");
  const groupSeparator = formatter.formatToParts(1000).find((part) => part.type === "group")?.value ?? ",";
  const decimalSeparator = formatter.formatToParts(1.1).find((part) => part.type === "decimal")?.value ?? ".";
  const integer = whole.replace(/\B(?=(\d{3})+(?!\d))/g, groupSeparator);
  const decimal = digits === 0 ? "" : decimalSeparator + fraction.slice(0, digits).padEnd(digits, "0");
  const prefix = integerIndex >= 0
    ? parts.slice(0, integerIndex).map((part) => part.value).join("")
    : "";
  const suffix = integerIndex >= 0
    ? parts.slice(integerIndex + 1)
      .filter((part) => !["group", "decimal", "fraction"].includes(part.type))
      .map((part) => part.value).join("")
    : "";
  return (negative ? "-" : "") + prefix + integer + decimal + suffix;
}

export const formatNaira = formatMoney;
