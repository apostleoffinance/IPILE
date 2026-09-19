"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SwitchProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

export const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, onCheckedChange, className, disabled, ...props }, ref) => (
    <button
      ref={ref}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange?.(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 rounded-full border border-line p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60 disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-accent" : "bg-subtle",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "block h-4 w-4 rounded-full bg-surface shadow-sm transition-transform",
          checked && "translate-x-5",
        )}
      />
    </button>
  ),
);
Switch.displayName = "Switch";