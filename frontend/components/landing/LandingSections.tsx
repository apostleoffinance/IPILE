"use client";

import Link from "next/link";
import { ArrowUpRight, Check, Menu, X } from "lucide-react";
import { useState } from "react";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { Wordmark } from "@/components/brand/Wordmark";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

const navItems = [
  { label: "How it works", href: "#how-it-works" },
  { label: "For families", href: "#family" },
  { label: "Wealth", href: "#wealth" },
  { label: "About", href: "#about" },
];

export function LandingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="relative z-20 border-b border-line/70 bg-canvas/95">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-10">
        <Wordmark size="sm" priority />
        <nav className="hidden items-center gap-8 text-sm text-muted md:flex" aria-label="Main navigation">
          {navItems.map((item) => <a key={item.href} href={item.href} className="transition-colors hover:text-ink">{item.label}</a>)}
        </nav>
        <div className="hidden items-center gap-5 text-sm md:flex">
          <ThemeToggle />
          <Link href="/login" className="text-muted transition-colors hover:text-ink">Sign in</Link>
          <Link href="/get-started" className="bg-accent px-4 py-2.5 text-inverse transition-colors hover:bg-accent-deep">Build your foundation <ArrowUpRight className="ml-1 inline h-4 w-4" aria-hidden="true" /></Link>
        </div>
        <button type="button" className="flex h-10 w-10 items-center justify-center border border-line md:hidden" onClick={() => setOpen((value) => !value)} aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}>
          {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
        </button>
      </div>
      {open ? <nav className="border-t border-line px-5 py-4 md:hidden" aria-label="Mobile navigation">
        <div className="space-y-1 text-sm">
          {navItems.map((item) => <a key={item.href} href={item.href} onClick={() => setOpen(false)} className="block border-b border-line py-3 text-muted">{item.label}</a>)}
          <div className="flex items-center justify-between border-b border-line py-3"><span className="text-muted">Appearance</span><ThemeToggle /></div>
          <Link href="/login" className="block py-3 text-muted">Sign in</Link>
          <Link href="/get-started" className="mt-2 block bg-accent px-4 py-3 text-center text-inverse">Build your foundation</Link>
        </div>
      </nav> : null}
    </header>
  );
}

export function SafeToSpendPreview() {
  const rows = [
    ["Income", "2000000.00", ""],
    ["Committed", "650000.00", "minus"],
    ["Protection", "150000.00", "minus"],
    ["Wealth building", "200000.00", "minus"],
    ["Buffer", "90000.00", "minus"],
  ] as const;
  return (
    <div className="relative border border-forest/30 bg-surface p-5 shadow-[14px_14px_0_var(--color-bg-subtle)] md:p-7">
      <div className="flex items-start justify-between border-b border-line pb-5">
        <div><p className="eyebrow text-gold">Household view</p><p className="mt-2 text-sm text-muted">September 2026 · All money</p></div>
        <span className="flex items-center gap-1 text-xs text-healthy"><span className="h-2 w-2 rounded-full bg-healthy" />Live picture</span>
      </div>
      <div className="py-7">
        <p className="eyebrow text-muted">Safe to spend</p>
        <p className="mt-2 font-display text-6xl leading-none text-ink md:text-7xl"><MoneyAmount amount="548000.00" /></p>
        <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted">Available after accounting for what matters.</p>
      </div>
      <div className="space-y-3 border-t border-line pt-5 text-sm">
        {rows.map(([label, amount, sign]) => <div key={label} className="flex items-center justify-between gap-4"><span className="text-muted">{label}</span><span className={sign === "minus" ? "tabular text-muted" : "tabular text-ink"}>{sign === "minus" ? "− " : "+ "}<MoneyAmount amount={amount} /></span></div>)}
      </div>
      <div className="mt-6 flex items-center justify-between border-t-2 border-forest pt-4"><span className="text-xs font-semibold uppercase tracking-[0.18em] text-forest">Safe to spend</span><span className="font-display text-2xl text-forest"><MoneyAmount amount="548000.00" /></span></div>
    </div>
  );
}

export function FinancialEcosystem() {
  const inputs = ["Income", "Accounts", "Bills", "Family", "Goals", "Savings", "Investments", "Business"];
  return <section id="how-it-works" className="border-y border-line bg-subtle/50 px-5 py-20 md:px-10 md:py-28"><div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.75fr_1.25fr] lg:items-center"><div><p className="eyebrow text-gold">The whole picture</p><h2 className="mt-4 max-w-lg font-display text-4xl leading-tight text-ink md:text-5xl">A family&apos;s money rarely lives in one place.</h2><p className="mt-6 max-w-md text-base leading-relaxed text-muted">Income arrives in one account. Bills leave another. Savings sit somewhere else. Family obligations live in your head. Goals get postponed.</p></div><div className="relative grid grid-cols-2 gap-2 sm:grid-cols-4">{inputs.map((item) => <span key={item} className="border border-line bg-surface px-3 py-4 text-center text-sm text-muted">{item}</span>)}<div className="col-span-2 mt-5 border border-forest bg-forest px-5 py-7 text-center text-inverse sm:col-span-4"><p className="eyebrow text-gold-bright">IPÌLẸ̀</p><p className="mt-2 font-display text-3xl">One household financial picture</p><p className="mx-auto mt-2 max-w-sm text-sm text-inverse/70">Clear enough to act on. Complete enough to trust.</p></div></div></div></section>;
}

export function FoundationPillars() {
  const pillars = [
    ["01", "Know your money", "Accounts, income, transactions and cash flow. Where money lives and moves."],
    ["02", "Plan what matters", "Budgets, obligations, bills and sinking funds. Prepare before due dates arrive."],
    ["03", "Build your wealth", "Savings, investments, goals, assets and net worth. Growth you can see."],
    ["04", "Make better decisions", "Safe to Spend, simulations and insights. Intelligence on verified numbers."],
  ];
  return <section className="px-5 py-20 md:px-10 md:py-28"><div className="mx-auto max-w-7xl"><div className="flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="eyebrow text-gold">One foundation</p><h2 className="mt-4 max-w-2xl font-display text-4xl leading-tight text-ink md:text-5xl">Everything your family needs to build financial stability.</h2></div><p className="max-w-xs text-sm leading-relaxed text-muted">Every naira has a job. IPÌLẸ̀ helps your household see which job comes next.</p></div><div className="mt-14 divide-y divide-line border-y border-line">{pillars.map(([number, title, body]) => <article key={number} className="group grid gap-5 py-7 transition-colors hover:bg-subtle/50 md:grid-cols-[70px_0.7fr_1fr] md:items-center"><span className="font-display text-2xl text-gold">{number}</span><h3 className="font-display text-3xl text-ink">{title}</h3><p className="max-w-md text-sm leading-relaxed text-muted">{body}</p></article>)}</div></div></section>;
}

export function FamilySection() {
  return <section id="family" className="bg-forest px-5 py-20 text-inverse md:px-10 md:py-28"><div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.9fr_1.1fr] lg:items-center"><div><p className="eyebrow text-gold-bright">Family</p><h2 className="mt-4 max-w-xl font-display text-5xl leading-tight">Money is personal. Financial life is shared.</h2><p className="mt-6 max-w-md text-base leading-relaxed text-inverse/70">Your finances aren&apos;t just about what you spend. They&apos;re about who you&apos;re responsible for, what you&apos;re preparing for, what you&apos;re building together, and what you want to leave behind.</p></div><div className="border-l border-gold/50 pl-6 md:pl-12"><p className="font-display text-3xl text-gold-bright">You</p><div className="mt-5 space-y-3 text-sm text-inverse/75"><p>├── Partner</p><p>├── Children &amp; dependants</p><p>├── Family obligations</p><p>├── Shared goals</p><p>└── Future</p></div></div></div></section>;
}

export function FoundationJourney() {
  const stages = [["Money clarity", "Know what you have and where it lives."], ["Planning", "Give every commitment a place in the picture."], ["Protection", "Prepare for the obligations you can already see."], ["Wealth", "Turn consistency into savings, investments and net worth."], ["Legacy", "Build a foundation the next season can stand on."]];
  return <section id="about" className="px-5 py-20 md:px-10 md:py-28"><div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.8fr_1.2fr]"><div><p className="eyebrow text-gold">Underneath it all</p><h2 className="mt-4 max-w-md font-display text-4xl leading-tight text-ink md:text-5xl">The infrastructure beneath a family&apos;s financial life.</h2></div><div className="border-t border-line">{stages.map(([title, body], index) => <div key={title} className="grid grid-cols-[36px_1fr] gap-4 border-b border-line py-5"><span className="pt-1 text-xs text-gold">0{index + 1}</span><div><h3 className="font-display text-2xl text-ink">{title}</h3><p className="mt-1 text-sm text-muted">{body}</p></div></div>)}</div></div></section>;
}

export function ProductPreview() {
  return <section className="border-y border-line bg-subtle/50 px-5 py-20 md:px-10 md:py-28"><div className="mx-auto max-w-7xl"><div className="max-w-xl"><p className="eyebrow text-gold">A window into IPÌLẸ̀</p><h2 className="mt-4 font-display text-4xl leading-tight text-ink md:text-5xl">See your family&apos;s financial picture clearly.</h2><p className="mt-5 text-base leading-relaxed text-muted">Not a collection of accounts. A calm view of what is safe, what needs attention, and what is getting stronger.</p></div><div className="mt-12 border border-forest/30 bg-surface p-4 shadow-[12px_12px_0_var(--color-bg-subtle)] md:p-7"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-5"><div><p className="eyebrow text-muted">Good morning, Family</p><p className="mt-1 text-sm text-muted">September 2026</p></div><span className="border border-healthy/30 px-3 py-1 text-xs text-healthy">Healthy household view</span></div><div className="grid gap-4 py-6 md:grid-cols-[1.15fr_0.85fr]"><div className="border border-forest bg-forest p-6 text-inverse"><p className="eyebrow text-gold-bright">Safe to spend</p><p className="mt-2 font-display text-5xl"><MoneyAmount amount="548000.00" /></p><p className="mt-2 text-sm text-inverse/70">After commitments, protection and wealth building.</p><div className="mt-7 h-2 bg-inverse/15"><div className="h-full w-[68%] bg-gold" /></div><div className="mt-2 flex justify-between text-xs text-inverse/60"><span>Committed</span><span>Freedom</span></div></div><div className="grid grid-cols-2 gap-3"><PreviewMetric label="Financial health" value="82 / 100" /><PreviewMetric label="Net worth" value="₦4.8M" /><PreviewMetric label="Emergency fund" value="₦900K" /><PreviewMetric label="Investments" value="₦2.1M" /></div></div><div className="grid gap-3 border-t border-line pt-5 md:grid-cols-2"><PreviewList title="Upcoming obligations" rows={[["University fees", "Due in 18 days"], ["Parents&apos; rent", "Due in 42 days"]]} /><PreviewList title="What needs attention?" rows={[["Food is nearing its plan", "Review budget"], ["Relocation goal is on track", "Keep going"]]} /></div></div></div></section>;
}

function PreviewMetric({ label, value }: { label: string; value: string }) { return <div className="border border-line p-4"><p className="text-xs text-muted">{label}</p><p className="mt-3 font-display text-2xl text-ink">{value}</p></div>; }
function PreviewList({ title, rows }: { title: string; rows: string[][] }) { return <div><p className="eyebrow text-muted">{title}</p><div className="mt-3 space-y-2">{rows.map(([name, detail]) => <div key={name} className="flex items-center justify-between gap-3 border border-line px-3 py-3 text-sm"><span className="text-ink">{name}</span><span className="text-xs text-muted">{detail}</span></div>)}</div></div>; }

export function DecisionSimulatorPreview() {
  return <section className="px-5 py-20 md:px-10 md:py-28"><div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[1fr_0.9fr] lg:items-center"><div><p className="eyebrow text-gold">Decision support</p><h2 className="mt-4 max-w-xl font-display text-4xl leading-tight text-ink md:text-5xl">Before you make a financial decision, see what it changes.</h2><p className="mt-6 max-w-md text-base leading-relaxed text-muted">IPÌLẸ̀ does more than record history. Its simulator helps your household understand the consequences before the decision becomes real.</p><Link href="/get-started" className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-accent underline underline-offset-4">Explore the foundation <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link></div><div className="border border-line bg-surface p-6"><div className="flex items-center justify-between"><p className="eyebrow text-muted">What if?</p><span className="text-xs text-warning">Scenario</span></div><h3 className="mt-6 font-display text-3xl text-ink">Income drops by 20%</h3><div className="mt-6 grid grid-cols-2 gap-3"><PreviewMetric label="Current" value="₦2.0M" /><PreviewMetric label="Projected" value="₦1.6M" /></div><div className="mt-6 space-y-3 border-t border-line pt-5 text-sm">{[["Safe to spend", "Adjusts first"], ["Emergency fund", "Protected"], ["Goals", "Slower path"], ["Surplus", "Recalculated"]].map(([label, value]) => <div key={label} className="flex items-center justify-between"><span className="text-muted">{label}</span><span className="flex items-center gap-2 text-ink"><Check className="h-4 w-4 text-healthy" aria-hidden="true" />{value}</span></div>)}</div></div></div></section>;
}

export function WealthSection() {
  const stages = ["Income", "Protection", "Savings", "Investments", "Net worth", "Legacy"];
  return <section id="wealth" className="bg-subtle/50 px-5 py-20 md:px-10 md:py-28"><div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-end"><div><p className="eyebrow text-gold">The long view</p><h2 className="mt-4 max-w-lg font-display text-4xl leading-tight text-ink md:text-5xl">Build something that lasts.</h2><p className="mt-6 max-w-md text-base leading-relaxed text-muted">Income is a starting point. Visibility and discipline turn it into protection, savings, investments, net worth and eventually, legacy.</p></div><div className="border-b-2 border-forest pb-4"><div className="flex items-end justify-between gap-2 text-xs uppercase tracking-[0.14em] text-muted">{stages.map((label, index) => <div key={label} className="flex min-w-0 flex-1 flex-col items-center gap-3 text-center"><span className="w-full max-w-12 bg-gold" style={{ height: `${(index + 2) * 8}px`, backgroundColor: index > 3 ? "var(--color-deep-forest)" : "var(--color-champagne-gold)" }} /><span className="text-[10px] leading-tight">{label}</span></div>)}</div></div></div></section>;
}

export function FinalCTA() {
  return <section className="bg-brand px-5 py-24 text-inverse md:px-10 md:py-32"><div className="mx-auto max-w-3xl text-center"><p className="eyebrow text-gold-bright">Start with clarity</p><h2 className="mt-5 font-display text-5xl leading-tight md:text-7xl">Build the foundation your family can build on.</h2><p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-inverse/70">Your family&apos;s money deserves more than a collection of accounts and spreadsheets. It deserves a foundation.</p><div className="mt-9 flex flex-wrap justify-center gap-5"><Link href="/get-started" className="bg-gold px-6 py-3 text-sm font-semibold text-brand transition-colors hover:bg-gold-bright">Build your foundation <ArrowUpRight className="ml-1 inline h-4 w-4" aria-hidden="true" /></Link><Link href="/login" className="px-4 py-3 text-sm text-inverse/70 underline underline-offset-4 hover:text-inverse">Already have an account? Sign in</Link></div></div></section>;
}

export function LandingFooter() {
  return <footer className="bg-brand px-5 pb-8 text-inverse md:px-10"><div className="mx-auto flex max-w-7xl flex-col gap-8 border-t border-inverse/15 pt-8 md:flex-row md:items-end md:justify-between"><div><Wordmark size="sm" /><p className="mt-3 text-sm text-inverse/60">The financial foundation for households everywhere.</p></div><div className="flex flex-wrap gap-x-6 gap-y-3 text-xs text-inverse/55"><a href="#how-it-works">Product</a><a href="#how-it-works">How it works</a><a href="#family">For families</a><a href="#about">About</a><Link href="/login">Sign in</Link><span>Privacy</span><span>Terms</span><span>Security</span></div></div><p className="mx-auto mt-10 max-w-7xl text-xs text-inverse/35">Money <span className="text-gold">·</span> Family <span className="text-gold">·</span> A brighter tomorrow</p></footer>;
}