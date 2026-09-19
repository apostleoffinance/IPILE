import { budgetSchema, obligationSchema, recurringSchema, transactionSchema } from "./forms";

function assert(condition: boolean, message: string) {
  if (!condition) throw new Error(message);
}

assert(transactionSchema.safeParse({
  type: "expense",
  amount: "150000.00",
  account_id: "acc-1",
  date: "2026-09-19",
}).success, "valid expense should pass");

assert(!transactionSchema.safeParse({
  type: "transfer",
  amount: "100.00",
  account_id: "acc-1",
  date: "2026-09-19",
}).success, "transfer without counterparty should fail");

assert(transactionSchema.safeParse({
  type: "transfer",
  amount: "100.00",
  account_id: "acc-1",
  counterparty_account_id: "acc-2",
  date: "2026-09-19",
}).success, "transfer with counterparty should pass");

assert(!transactionSchema.safeParse({
  type: "expense",
  amount: "15,000.00",
  account_id: "acc-1",
  date: "2026-09-19",
}).success, "comma amount should fail");

assert(transactionSchema.safeParse({
  type: "expense",
  amount: "150000",
  account_id: "acc-1",
  date: "2026-09-19",
}).success, "integer amount string should pass");

assert(budgetSchema.safeParse({
  name: "Essentials",
  period_type: "monthly",
  categories: [{ category_id: "cat-1", allocated_amount: "250000.00" }],
}).success, "monthly budget should pass");

assert(!budgetSchema.safeParse({
  name: "Custom",
  period_type: "custom",
  categories: [{ category_id: "cat-1", allocated_amount: "10.00" }],
}).success, "custom budget without dates should fail");

assert(obligationSchema.safeParse({
  name: "Rent",
  amount: "450000.00",
  frequency: "monthly",
  next_due_date: "2026-10-01",
  sinking_fund: false,
}).success, "obligation should pass");

assert(recurringSchema.safeParse({
  type: "expense",
  amount: "40000.00",
  account_id: "acc-1",
  frequency: "monthly",
  next_date: "2026-10-01",
}).success, "recurring should pass");

assert(!recurringSchema.safeParse({
  type: "transfer",
  amount: "100.00",
  account_id: "acc-1",
  frequency: "weekly",
  next_date: "2026-10-01",
}).success, "recurring transfer without counterparty should fail");

console.log("forms tests ok");
