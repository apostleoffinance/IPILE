"use client";

import Link from "next/link";
import { AppShell } from "@/components/shared/AppShell";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";

const areas = [
  { href: "/plan/budget", title: "Budgets", detail: "Set category and member plans, then monitor actual spending.", label: "Spending guardrails" },
  { href: "/plan/obligations", title: "Obligations", detail: "Prepare for bills, commitments and upcoming due dates.", label: "Commitments" },
  { href: "/plan/funds", title: "Funds", detail: "Build reserves toward planned targets and linked obligations.", label: "Reserves" },
  { href: "/plan/recurring", title: "Recurring", detail: "Manage repeating income, expenses and transfers.", label: "Repeat activity" },
  { href: "/plan/allocation", title: "Allocation", detail: "Apply household-defined rules to recognized income.", label: "Distribution rules" },
];

export default function PlanWorkspacePage() {
  return <AppShell><ContentContainer className="ipile-workspace ipile-plan-workspace">
    <PageHeader eyebrow="Household planning" title="Plan" description="Give every naira a deliberate purpose: prepare for commitments, build reserves and keep spending aligned with your priorities." />
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {areas.map((area) => <Link key={area.href} href={area.href} className="group flex min-h-44 flex-col justify-between rounded-xl border border-line bg-surface p-5 transition hover:-translate-y-0.5 hover:border-accent">
        <div><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted">{area.label}</p><h2 className="mt-3 text-xl font-medium tracking-tight">{area.title}</h2><p className="mt-2 max-w-sm text-sm leading-relaxed text-muted">{area.detail}</p></div>
        <span className="mt-5 text-sm font-medium text-accent">Open workspace <span aria-hidden="true">↗</span></span>
      </Link>)}
    </section>
    <p className="text-xs leading-relaxed text-muted">Planning views use your recorded budgets, obligations, funds, recurring templates and allocation rules. Missing data is not replaced with sample values.</p>
  </ContentContainer></AppShell>;
}
