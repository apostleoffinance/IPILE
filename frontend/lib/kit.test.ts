import { cn } from "./utils";
import { moneyDelta, moneySign } from "./money-change";
import { decisionHrefForPattern } from "./decision-routing";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

assert(cn("px-2", "px-4") === "px-4", "cn should merge conflicting tailwind classes");
assert(cn("text-ink", false && "hidden", "font-medium") === "text-ink font-medium", "cn should drop falsy");

assert(moneySign("10.00") === "positive", "positive amount");
assert(moneySign("-1.00") === "negative", "negative amount");
assert(moneySign("0.00") === "neutral", "zero amount");
assert(moneyDelta("100.00", "80.00") === "20.00", "delta math");
assert(moneyDelta("80.00", "100.00") === "-20.00", "negative delta");

assert(decisionHrefForPattern("budget_overspend") === "/plan/budget", "budget pattern route");
assert(decisionHrefForPattern("giving_limit") === "/family/giving", "giving pattern route");
assert(decisionHrefForPattern("unknown_code") === "/insights", "fallback route");

console.log("kit helpers tests ok");
