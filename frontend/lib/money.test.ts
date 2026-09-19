import { formatNaira, parseMoney } from "./money";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

const formatCases: Array<[string, string, string?]> = [
  ["2000000", "₦2,000,000.00"],
  ["2000000.00", "₦2,000,000.00"],
  ["150000.5", "₦150,000.50"],
  ["0", "₦0.00"],
  ["0.01", "₦0.01"],
  ["-45000.25", "-₦45,000.25"],
  ["1000", "USD 1,000.00", "USD"],
];

for (const [input, expected, currency] of formatCases) {
  const got = formatNaira(input, currency);
  assert(got === expected, `formatNaira(${input}, ${currency ?? "NGN"}) => ${got}, expected ${expected}`);
}

assert(parseMoney("90") === "90.00", "parseMoney should pad cents");
assert(parseMoney("90.5") === "90.50", "parseMoney should pad single fractional digit");
assert(parseMoney("-12.3") === "-12.30", "parseMoney should keep sign");

let threw = false;
try {
  parseMoney("abc");
} catch {
  threw = true;
}
assert(threw, "parseMoney should reject non-decimal");

threw = false;
try {
  parseMoney("1.234");
} catch {
  threw = true;
}
assert(threw, "parseMoney should reject >2 fractional digits");

console.log("money tests ok");
