"use client";

import { FormEvent, useEffect, useState } from "react";
import { DecisionCard } from "@/components/financial/DecisionCard";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { MoneyChange } from "@/components/financial/MoneyChange";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { api, runSimulation, type Obligation, type SimulationRun } from "@/lib/api";

export default function SimulatePage() {
  const currency = useHouseholdCurrency();
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
      <ContentContainer>
        <PageHeader
          eyebrow="Intelligence"
          title="Simulator"
          description="What happens if? Runs on a cloned household. Live balances do not move."
        />
        <SectionHeader title="Scenario" />
        <form onSubmit={onSubmit} className="grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
          <div>
            <Label htmlFor="sim-income">Income change rate</Label>
            <Input
              id="sim-income"
              className="mt-1"
              value={incomeRate}
              onChange={(event) => setIncomeRate(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="sim-unexpected">Unexpected expense</Label>
            <Input
              id="sim-unexpected"
              className="mt-1 tabular"
              value={unexpected}
              onChange={(event) => setUnexpected(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="sim-obligation">Obligation</Label>
            <Select
              id="sim-obligation"
              className="mt-1"
              value={feeId}
              onChange={(event) => setFeeId(event.target.value)}
            >
              {obligations.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="sim-fee">Obligation change rate</Label>
            <Input
              id="sim-fee"
              className="mt-1"
              value={feeRate}
              onChange={(event) => setFeeRate(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="sim-horizon">Horizon (months)</Label>
            <Input
              id="sim-horizon"
              className="mt-1"
              value={horizon}
              onChange={(event) => setHorizon(event.target.value)}
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={pending}>
              {pending ? "Running..." : "Run simulation"}
            </Button>
          </div>
        </form>
        {error ? <ErrorState message={error} /> : null}
        {pending && !result ? <LoadingState /> : null}
        {result ? (
          <section className="space-y-6">
            <SectionHeader title="Outcome" description={result.name} />
            <div className="grid gap-3 md:grid-cols-3">
              <Status label="Cash flow" value={result.summary.cash_flow} />
              <Status label="Obligations" value={result.summary.obligations} />
              <Status label="Emergency" value={result.summary.emergency_fund} />
              <Status label="Investments" value={result.summary.investments_status} />
              <Status label="Safe to Spend" value={result.summary.safe_to_spend} />
              <div className="border border-line bg-surface p-4">
                <p className="text-xs uppercase tracking-wide text-muted">Net worth delta</p>
                <p className="mt-2">
                  <MoneyChange amount={result.summary.net_worth_delta} currency={currency ?? "NGN"} />
                </p>
              </div>
            </div>
            {(result.summary.cash_flow === "critical" ||
              result.summary.obligations === "unfunded" ||
              result.summary.safe_to_spend === "critical") && (
              <DecisionCard
                title="This scenario stresses the household"
                body="Review obligations and Safe to Spend before acting on a similar change in real life."
                href="/overview"
                severity="warning"
              />
            )}
            <SectionHeader title="Month path" />
            <div className="space-y-2">
              {result.months.map((row) => (
                <div
                  key={row.month_index}
                  className="flex flex-wrap justify-between gap-2 border border-line bg-surface px-4 py-3 text-sm"
                >
                  <span>Month {row.month_index}</span>
                  <span className="tabular">
                    Income <MoneyAmount amount={row.income} currency={currency ?? "NGN"} /> · surplus{" "}
                    <MoneyAmount amount={row.surplus} currency={currency ?? "NGN"} /> · {row.cash_flow}
                  </span>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </ContentContainer>
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
    <div className="border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 capitalize ${tone}`}>{value.replaceAll("_", " ")}</p>
    </div>
  );
}
