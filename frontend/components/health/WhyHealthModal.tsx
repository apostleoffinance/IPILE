import { useEffect, useState } from "react";
import { Modal } from "@/components/shared/Modal";
import { explainFinancialHealth, type HealthScore } from "@/lib/api";

export function WhyHealthModal({
  fallback,
  onClose,
}: {
  fallback: HealthScore;
  onClose: () => void;
}) {
  const [health, setHealth] = useState<HealthScore>(fallback);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    explainFinancialHealth().then(setHealth).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <Modal title={`Why ${health.score}?`} onClose={onClose}>
      <div className="max-h-[70vh] space-y-4 overflow-y-auto text-sm">
        <p className="text-muted">
          {health.label} · components sum to {health.score}. Weights are from the household health engine.
        </p>
        {error ? <p className="text-critical">{error}</p> : null}
        {health.components.map((row) => (
          <div key={row.key} className="rounded-md border border-line p-3">
            <div className="flex items-baseline justify-between">
              <p className="capitalize">{row.key.replaceAll("_", " ")}</p>
              <p className="tabular">
                {row.points} / {row.weight}
              </p>
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-muted">
              {Object.entries(row.inputs).map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="capitalize">{key.replaceAll("_", " ")}</dt>
                  <dd className="tabular text-right text-ink">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </Modal>
  );
}
