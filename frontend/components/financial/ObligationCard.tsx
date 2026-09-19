import Link from "next/link";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import type { CalendarEvent } from "@/lib/api";
import { obligationCoverageTone } from "@/lib/financial-kit";
import { cn } from "@/lib/utils";

type ObligationCardProps = {
  event: CalendarEvent;
  currency: string;
  href?: string;
  className?: string;
};

export function ObligationCard({ event, currency, href = "/plan/obligations", className }: ObligationCardProps) {
  const body = (
    <div
      className={cn(
        "flex items-baseline justify-between gap-4 border border-line bg-surface px-4 py-3 transition-colors hover:border-accent/30",
        className,
      )}
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{event.title}</p>
        <p className="mt-1 text-xs capitalize text-muted">
          {event.date} · {event.status}
          {event.coverage_label ? (
            <>
              {" · "}
              <span className={obligationCoverageTone(event.coverage_label)}>{event.coverage_label}</span>
            </>
          ) : null}
        </p>
      </div>
      <MoneyAmount amount={event.amount} currency={currency} className="shrink-0 text-sm font-medium" />
    </div>
  );

  return (
    <Link
      href={href}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50"
      aria-label={`${event.title}, ${event.amount}, due ${event.date}`}
    >
      {body}
    </Link>
  );
}
