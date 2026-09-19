import { FormEvent, useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { Modal } from "@/components/shared/Modal";
import { runPurchaseCheck, type PurchaseCheckResult, type SafeToSpendSnapshot } from "@/lib/api";

export function PurchaseCheckModal({
  currency,
  snapshot,
  onClose,
}: {
  currency: string;
  snapshot: SafeToSpendSnapshot;
  onClose: () => void;
}) {
  const [amount, setAmount] = useState("180000.00");
  const [result, setResult] = useState<PurchaseCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      setResult(await runPurchaseCheck({ amount }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not check purchase.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title="Purchase check" onClose={onClose}>
      <div className="space-y-4 text-sm">
        <div className="grid grid-cols-3 gap-2">
          <Metric label="Current" amount={snapshot.current} currency={currency} />
          <Metric label="Period" amount={snapshot.period} currency={currency} />
          <Metric label="Forecast" amount={snapshot.forecast} currency={currency} />
        </div>
        <form onSubmit={submit} className="space-y-3">
          <label className="block">
            <span className="text-xs uppercase tracking-wide text-muted">Purchase amount</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-canvas px-3 py-2"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              inputMode="decimal"
            />
          </label>
          {error ? <p className="text-critical">{error}</p> : null}
          <button
            type="submit"
            disabled={pending}
            className="rounded-md bg-ink px-4 py-2 text-canvas disabled:opacity-50"
          >
            {pending ? "Checking..." : "Check affordability"}
          </button>
        </form>
        {result ? (
          <div className="rounded-md border border-line p-3">
            <p className="capitalize text-muted">{result.severity}</p>
            <p className="mt-1">{result.affordable ? "Affordable" : "Not affordable"}</p>
            <p className="mt-2">
              Remaining Safe to Spend{" "}
              <MoneyAmount amount={result.remaining_current_sts} currency={currency} />
            </p>
            {result.buffer_breached ? (
              <p className="mt-2 text-warning">This would breach the household minimum buffer.</p>
            ) : null}
            <p className="mt-2 text-muted">Recommended: {result.recommended_action}</p>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

function Metric({ label, amount, currency }: { label: string; amount: string; currency: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1">
        <MoneyAmount amount={amount} currency={currency} />
      </p>
    </div>
  );
}
