import * as React from "react";
import { cn } from "@/lib/utils";

export const Checkbox = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "checkbox", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "h-4 w-4 accent-[var(--color-accent-primary)] focus-visible:ring-2 focus-visible:ring-gold/60",
        className,
      )}
      {...props}
    />
  ),
);
Checkbox.displayName = "Checkbox";