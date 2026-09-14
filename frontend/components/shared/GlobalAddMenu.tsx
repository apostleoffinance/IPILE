"use client";

import Link from "next/link";
import { useEffect } from "react";

const ACTIONS = [
  { href: "/money/income", label: "Income", hint: "Record money coming in" },
  { href: "/money/transactions", label: "Expense", hint: "Capture spending" },
  { href: "/money/transactions", label: "Transfer", hint: "Move between accounts" },
  { href: "/plan/obligations", label: "Obligation", hint: "What must you prepare for?" },
  { href: "/wealth/goals", label: "Goal", hint: "What are you building toward?" },
  { href: "/money/accounts", label: "Account", hint: "Where money lives" },
  { href: "/wealth", label: "Asset / debt", hint: "Track wealth position" },
];

export function GlobalAddMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-brand/50 px-4 pb-24 md:items-center md:pb-0">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="Close" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md border border-line bg-surface p-5 shadow-xl">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">Add</p>
        <h2 className="mt-1 font-display text-2xl text-ink">What would you like to add?</h2>
        <ul className="mt-5 divide-y divide-line">
          {ACTIONS.map((action) => (
            <li key={action.label}>
              <Link
                href={action.href}
                onClick={onClose}
                className="flex flex-col py-3 transition hover:bg-subtle"
              >
                <span className="text-sm font-medium text-ink">{action.label}</span>
                <span className="text-xs text-muted">{action.hint}</span>
              </Link>
            </li>
          ))}
        </ul>
        <button type="button" className="mt-4 text-sm text-muted underline" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  );
}
