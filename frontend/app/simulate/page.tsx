"use client";

import { FormEvent, useEffect, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, runSimulation, type Obligation, type SimulationRun } from "@/lib/api";

export default function SimulatePage() {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [incomeRate, setIncomeRate] = useState("-0.20");
  const [unexpected, setUnexpected] = useState("300000.00");
  const [feeRate, setFeeRate] = useState("0.15");
  const [feeId, setFeeId] = useState("");
  const [horizon, setHorizon] = useState("12");
  const [result, setResult] = useState<SimulationRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api
      .obligations()
      .then((rows) => {
        setObligations(rows);
        const university = rows.find((row) => row.frequency === "quarterly") ?? rows[0];
        if (university) setFeeId(university.id);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const obligation_deltas: Record<string, string> = {};
      if (feeId) obligation_deltas[feeId] = feeRate;
      setResult(
        await runSimulation({
          name: "What if",
          income_change_rate: incomeRate,
          unexpected_expense: unexpected || undefined,
          obligation_deltas,
          horizon_months: Number(horizon),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16">
        <div>
          <p className="text-sm text-muted">What happens if?</p>
          <h1 className="mt-1 text-3xl font-medium">Simulator</h1>
          <p className="mt-2 text-sm text-muted">
            Runs on a cloned household. Live balances do not move.
          </p>
        </div>
        <form onSubmit={onSubmit} className="grid gap-4 rounded-md border border-line bg-surface p-5 md:grid-cols-2">
          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-muted">Income change rate</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={incomeRate}
              onChange={(event) => setIncomeRate(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-muted">Unexpected expense</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={unexpected}
              onChange={(event) => setUnexpected(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-muted">Obligation</span>
            <select
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={feeId}
              onChange={(event) => setFeeId(event.target.value)}
            >
              {obligations.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-muted">Obligation change rate</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={feeRate}
              onChange={(event) => setFeeRate(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-xs uppercase tracking-wide text-muted">Horizon (months)</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={horizon}
              onChange={(event) => setHorizon(event.target.value)}
            />
          </label>
          <div className="flex items-end">
            <button type="submit" disabled={pending} className="rounded-md bg-ink px-4 py-2 text-canvas disabled:opacity-50">
              {pending ? "Running…" : "Run simulation"}
            </button>
          </div>
        </form>
        {error ? <ErrorState message={error} /> : null}
        {pending && !result ? <LoadingState /> : null}
        {result ? (
          <section className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Status label="Cash flow" value={result.summary.cash_flow} />
              <Status label="Obligations" value={result.summary.obligations} />
              <Status label="Emergency" value={result.summary.emergency_fund} />
              <Status label="Investments" value={result.summary.investments_status} />
              <Status label="Safe to Spend" value={result.summary.safe_to_spend} />
              <div className="rounded-md border border-line bg-surface p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Net worth delta</p>
                <p className="mt-2">
                  <MoneyAmount amount={result.summary.net_worth_delta} currency="NGN" />
                </p>
              </div>
            </div>
            <div className="space-y-2">
              {result.months.map((row) => (
                <div
                  key={row.month_index}
                  className="flex flex-wrap justify-between gap-2 rounded-md border border-line bg-surface px-4 py-3 text-sm"
                >
                  <span>Month {row.month_index}</span>
                  <span className="tabular">
                    Income <MoneyAmount amount={row.income} currency="NGN" /> · surplus{" "}
                    <MoneyAmount amount={row.surplus} currency="NGN" /> · {row.cash_flow}
                  </span>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}

function Status({ label, value }: { label: string; value: string }) {
  const tone =
    value === "critical" || value === "unfunded" || value === "paused"
      ? "text-critical"
      : value === "warning" || value === "at risk" || value === "reduced"
        ? "text-warning"
        : "text-healthy";
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 capitalize ${tone}`}>{value.replaceAll("_", " ")}</p>
    </div>
  );
}
