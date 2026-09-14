export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <p className="text-sm text-muted">{label}…</p>;
}
