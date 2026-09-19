import * as React from "react";
import { cn } from "@/lib/utils";

export function FinancialForm({
  children,
  onSubmit,
  className,
  pending = false,
}: {
  children: React.ReactNode;
  onSubmit: React.FormEventHandler<HTMLFormElement>;
  className?: string;
  pending?: boolean;
}) {
  return (
    <form
      onSubmit={onSubmit}
      aria-busy={pending}
      className={cn("grid gap-4 border border-line bg-surface p-5", pending && "opacity-80", className)}
    >
      {children}
    </form>
  );
}