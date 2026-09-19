"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function DropdownMenu({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <details className={cn("relative", className)}>
      <summary className="flex h-10 cursor-pointer list-none items-center justify-center border border-line bg-surface px-3 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60">
        {label}
      </summary>
      <div className="absolute right-0 top-11 z-40 min-w-48 border border-line bg-surface p-1 shadow-soft">
        {children}
      </div>
    </details>
  );
}

export function DropdownMenuItem({
  children,
  onSelect,
  className,
}: {
  children: React.ReactNode;
  onSelect?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={cn("flex w-full px-3 py-2 text-left text-sm text-ink hover:bg-subtle", className)}
      onClick={onSelect}
    >
      {children}
    </button>
  );
}