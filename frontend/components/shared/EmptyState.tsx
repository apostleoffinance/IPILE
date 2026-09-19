import * as React from "react";
import Link from "next/link";

type EmptyStateProps = {
  title: string;
  body: string;
  actionLabel?: string;
  actionHref?: string;
};

export function EmptyState({ title, body, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="border border-line bg-surface px-6 py-10 text-center">
      <h2 className="font-display text-2xl text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-5 inline-block bg-accent px-4 py-2 text-sm text-white"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
