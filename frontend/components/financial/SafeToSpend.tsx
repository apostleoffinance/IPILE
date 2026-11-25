"use client";

import * as React from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { Button } from "@/components/ui/button";
import type { SafeToSpendSnapshot } from "@/lib/api";
import { cn } from "@/lib/utils";

type SafeToSpendProps = {
  snapshot: SafeToSpendSnapshot;
  currency: string;
  onInspect?: () => void;
  className?: string;
  label?: string;
  description?: string;
};

export function SafeToSpend({
  snapshot,
  currency,
  onInspect,
  className,
  label = "Safe to spend",
  description = "You can safely spend this without affecting commitments IPÌLẸ̀ already knows about.",
}: SafeToSpendProps) {
  return (
    <section
      className={cn("ipile-safe-to-spend relative overflow-hidden border border-accent/20 bg-accent px-6 py-8 text-inverse md:px-10", className)}
      aria-label={label}
    >
      <div className="ipile-safe-header"><p className="text-xs uppercase tracking-[0.25em] text-gold-bright">{label}</p><span className="ipile-safe-status">Based on your recorded commitments</span></div>
      <p className="ipile-safe-amount mt-3 font-display text-5xl tabular md:text-6xl">
        <MoneyAmount amount={snapshot.current} currency={currency} />
      </p>
      <p className="mt-3 max-w-xl text-sm text-inverse/80">{description}</p>
      <div className="ipile-safe-details mt-5 grid grid-cols-1 gap-3 text-sm text-inverse/75 sm:grid-cols-3">
        <div className="ipile-safe-detail">
          <p className="text-xs uppercase tracking-wide text-gold-bright/80">Period</p>
          <p className="mt-1 tabular">
            <MoneyAmount amount={snapshot.period} currency={currency} />
          </p>
        </div>
        <div className="ipile-safe-detail">
          <p className="text-xs uppercase tracking-wide text-gold-bright/80">Forecast</p>
          <p className="mt-1 tabular">
            <MoneyAmount amount={snapshot.forecast} currency={currency} />
          </p>
        </div>
        <div className="ipile-safe-detail">
          <p className="text-xs uppercase tracking-wide text-gold-bright/80">Buffer</p>
          <p className="mt-1 tabular">
            <MoneyAmount amount={snapshot.minimum_buffer_amount} currency={currency} />
          </p>
        </div>
      </div>
      {onInspect ? (
        <Button
          type="button"
          variant="link"
          className="mt-5 h-auto p-0 text-gold-bright"
          onClick={onInspect}
        >
          View calculation / check a purchase
        </Button>
      ) : null}
    </section>
  );
}
