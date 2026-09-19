import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SafeToSpend } from "@/components/financial/SafeToSpend";
import { HealthScore } from "@/components/health/HealthScore";
import { EmptyState } from "@/components/shared/EmptyState";

const snapshot = {
  currency: "USD",
  current: "1250.00",
  period: "2100.00",
  forecast: "1800.00",
  horizon_days: 30,
  minimum_buffer_amount: "300.00",
  components: {
    liquid_cash: "2000.00",
    expected_income: "500.00",
    committed_obligations: "600.00",
    upcoming_bills: "250.00",
    sinking_fund_requirements: "100.00",
    protected_savings: "200.00",
    pending_transactions: "100.00",
  },
};

const safeToSpendMarkup = renderToStaticMarkup(
  React.createElement(SafeToSpend, { snapshot, currency: "USD", onInspect: () => undefined }),
);
assert(safeToSpendMarkup.includes("Safe to spend"), "Safe to Spend label is visible");
assert(safeToSpendMarkup.includes("USD 1,250.00"), "Safe to Spend uses the supplied currency");
assert(safeToSpendMarkup.includes("View calculation"), "Safe to Spend exposes an inspection action when available");

const healthMarkup = renderToStaticMarkup(
  React.createElement(HealthScore, {
    health: {
      score: "82.00",
      label: "Healthy",
      period_start: "2026-09-01",
      period_end: "2026-09-30",
      components: [],
    },
  }),
);
assert(healthMarkup.includes("82.00"), "Health score is visible");
assert(healthMarkup.includes("Why 82.00?"), "Health explanation affordance is visible");

const emptyMarkup = renderToStaticMarkup(
  React.createElement(EmptyState, {
    title: "No accounts yet",
    body: "Add an account to understand available cash.",
  }),
);
assert(emptyMarkup.includes("No accounts yet"), "Empty state title is visible");
assert(emptyMarkup.includes("Add an account to understand available cash."), "Empty state guidance is visible");

console.log("component rendering tests ok");