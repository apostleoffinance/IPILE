"use client";

import Link from "next/link";
import { AppShell } from "@/components/shared/AppShell";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";

const areas = [
  { href: "/money/transactions", title: "Transactions", detail: "Record, review, categorize and correct ledger activity.", label: "Ledger" },
  { href: "/money/accounts", title: "Accounts", detail: "Understand where household cash and balances are held.", label: "Balances" },
  { href: "/money/income", title: "Income", detail: "Manage income sources and recognize received income.", label: "Inflow" },
  { href: "/money/cash-flow", title: "Cash flow", detail: "Review daily inflows, outflows and closing cash.", label: "Movement" },
  { href: "/money/import", title: "Statement import", detail: "Preview bank exports and confirm staged transactions.", label: "Import" },
  { href: "/money/reconciliation", title: "Reconciliation", detail: "Match statement activity to the household ledger.", label: "Control" },
  { href: "/money/receipts", title: "Receipts", detail: "Review extracted receipt details before posting expenses.", label: "Documents" },
];

export default function MoneyWorkspacePage() {
  return <AppShell><ContentContainer className="ipile-workspace ipile-money-workspace">
    <PageHeader eyebrow="Household finances" title="Money" description="A clear view of where money lives, what moved, and whether your records agree." />
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {areas.map((area) => <Link key={area.href} href={area.href} className="group flex min-h-44 flex-col justify-between rounded-xl border border-line bg-surface p-5 transition hover:-translate-y-0.5 hover:border-accent">
        <div><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted">{area.label}</p><h2 className="mt-3 text-xl font-medium tracking-tight">{area.title}</h2><p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">{area.detail}</p></div>
        <span className="mt-5 text-sm font-medium text-accent">Open workspace <span aria-hidden="true">↗</span></span>
      </Link>)}
    </section>
    <p className="text-xs leading-relaxed text-muted">Balances and activity are drawn from your household records. No estimates or sample figures are substituted for missing data.</p>
  </ContentContainer></AppShell>;
}
