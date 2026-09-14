import { formatNaira, parseMoney } from "./money";

const cases: Array<[string, string]> = [
  ["2000000", "₦2,000,000.00"],
  ["2000000.00", "₦2,000,000.00"],
  ["150000.5", "₦150,000.50"],
];

for (const [input, expected] of cases) {
  if (formatNaira(input) !== expected) {
    throw new Error(`formatNaira(${input}) !== ${expected}`);
  }
}

if (parseMoney("90") !== "90.00") {
  throw new Error("parseMoney should pad cents");
}

console.log("money tests ok");
