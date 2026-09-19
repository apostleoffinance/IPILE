import Link from "next/link";
import { AlertTriangle, CircleDot, Info } from "lucide-react";
import {
  decisionIconTone,
  decisionSeverityClass,
  type DecisionSeverity,
} from "@/lib/financial-kit";
import { cn } from "@/lib/utils";

export type { DecisionSeverity };

export type DecisionCardProps = {
  title: string;
  body: string;
  href: string;
  severity?: DecisionSeverity;
  className?: string;
};

const severityIcons: Record<DecisionSeverity, typeof AlertTriangle> = {
  warning: AlertTriangle,
  critical: AlertTriangle,
  neutral: CircleDot,
  info: Info,
};

export function DecisionCard({
  title,
  body,
  href,
  severity = "neutral",
  className,
}: DecisionCardProps) {
  const Icon = severityIcons[severity];
  return (
    <Link
      href={href}
      className={cn(
        "flex gap-3 border bg-surface px-4 py-3 transition-colors hover:border-accent/35",
        decisionSeverityClass(severity),
        className,
      )}
      aria-label={`${title}. ${body}`}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", decisionIconTone(severity))} aria-hidden />
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">{title}</p>
        <p className="mt-1 text-sm text-muted">{body}</p>
      </div>
    </Link>
  );
}
