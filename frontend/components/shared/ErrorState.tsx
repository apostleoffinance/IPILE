export function ErrorState({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-critical/20 bg-surface px-4 py-3 text-sm text-critical">
      {message}
    </p>
  );
}
