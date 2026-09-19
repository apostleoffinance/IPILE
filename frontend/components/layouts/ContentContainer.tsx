import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function ContentContainer({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("mx-auto w-full max-w-6xl space-y-8 pb-20", className)}>{children}</div>;
}
