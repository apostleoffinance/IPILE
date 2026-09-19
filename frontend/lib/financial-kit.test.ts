import {
  decisionIconTone,
  decisionSeverityClass,
  obligationCoverageTone,
  safeToSpendReady,
  sumMoneyStrings,
  transactionDisplayLabel,
} from "./financial-kit";
import { formatNaira } from "./money";
import { moneyDelta, moneySign } from "./money-change";
import { decisionHrefForPattern } from "./decision-routing";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

assert(decisionSeverityClass("critical") === "border-critical/40", "critical border");
assert(decisionSeverityClass("neutral") === "border-line", "neutral border");
assert(decisionIconTone("info") === "text-info", "info icon tone");
assert(obligationCoverageTone("funded") === "text-healthy", "funded tone");
assert(obligationCoverageTone("partial") === "text-warning", "partial tone");
assert(obligationCoverageTone("unfunded") === "text-critical", "unfunded tone");

assert(
  transactionDisplayLabel({ description: "Rent", merchant: "X", type: "expense" }) === "Rent",
  "prefer description",
);
assert(
  transactionDisplayLabel({ description: null, merchant: "Shop", type: "expense" }) === "Shop",
  "fallback merchant",
);
assert(transactionDisplayLabel({ description: null, merchant: null, type: "giving" }) === "giving", "fallback type");

assert(sumMoneyStrings(["100.00", "50.50", "0.50"]) === "151.00", "sum money");
assert(sumMoneyStrings(["-20.00", "30.00"]) === "10.00", "sum with negative");

assert(
  safeToSpendReady({
    liquid_cash: "1000.00",
    expected_income: "0.00",
    committed_obligations: "100.00",
    upcoming_bills: "0.00",
    sinking_fund_requirements: "0.00",
    protected_savings: "0.00",
    pending_transactions: "0.00",
  }),
  "sts ready",
);
assert(!safeToSpendReady(null), "sts null not ready");
assert(!safeToSpendReady({ liquid_cash: "abc" }), "sts invalid not ready");

assert(formatNaira(sumMoneyStrings(["2000000.00", "150000.00"])) === "₦2,150,000.00", "format summed");
assert(moneySign(moneyDelta("90.00", "100.00")) === "negative", "delta sign");
assert(decisionHrefForPattern("obligation_underfunded") === "/plan/obligations", "obligation route");

console.log("financial kit tests ok");
