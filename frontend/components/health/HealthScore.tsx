import type { HealthScore as HealthScoreType } from "@/lib/api";

const labelClass: Record<string, string> = {
  Healthy: "text-healthy",
  Watch: "text-warning",
  Strained: "text-warning",
  Critical: "text-critical",
};

export function HealthScore({
  health,
  onOpen,
}: {
  health: HealthScoreType;
  onOpen?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full border border-line bg-surface p-5 text-left"
    >
      <p className="text-xs uppercase tracking-[0.2em] text-muted">Financial health</p>
      <p className="mt-2 font-display text-5xl tabular">
        {health.score} <span className="text-lg text-muted">/ 100</span>
      </p>
      <p className={`mt-2 text-sm ${labelClass[health.label] ?? "text-muted"}`}>{health.label}</p>
      <p className="mt-1 text-sm text-muted">Why {health.score}? — every weighted component.</p>
    </button>
  );
}
