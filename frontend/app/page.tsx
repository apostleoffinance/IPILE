"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, setHouseholdId } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        if (!me.households || me.households.length === 0) {
          router.replace("/onboarding");
          return;
        }
        setHouseholdId(me.households[0].id);
        router.replace("/overview");
      })
      .catch(() => setChecking(false));
  }, [router]);

  if (checking) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-brand text-[#9fb8ad]">
        <LoadingState label="Opening IPÌLẸ̀" />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-brand text-[#e8efe9]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 md:px-10">
        <div>
          <Wordmark tone="dark" />
          <p className="mt-1 hidden text-[11px] uppercase tracking-[0.2em] text-[#7f9a8e] sm:block">
            Financial foundation for households
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Link href="/login" className="px-3 py-2 text-[#9fb8ad] hover:text-gold-bright">
            Sign in
          </Link>
          <Link
            href="/get-started"
            className="border border-gold/60 bg-transparent px-4 py-2 text-gold-bright transition hover:bg-gold/10"
          >
            Get started
          </Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-10 md:grid-cols-[1.15fr_0.85fr] md:items-center md:px-10 md:pt-16">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-gold">IPÌLẸ̀</p>
          <h1 className="mt-4 font-display text-4xl leading-tight text-[#f4f7f5] md:text-6xl">
            Your family&apos;s money.
            <br />
            One foundation.
          </h1>
          <p className="mt-5 max-w-xl text-base text-[#9fb8ad] md:text-lg">
            IPÌLẸ̀ helps households organize their money, plan commitments, control spending and build
            wealth together.
          </p>
          <p className="mt-4 text-sm tracking-wide text-[#7f9a8e]">
            Know your money. Plan what matters. Build what lasts.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/get-started"
              className="bg-gold px-5 py-3 text-sm font-medium text-brand transition hover:bg-gold-bright"
            >
              Build your foundation →
            </Link>
            <Link href="/login" className="text-sm text-[#9fb8ad] underline-offset-4 hover:text-gold-bright hover:underline">
              Already have an account? Sign in
            </Link>
          </div>
        </div>

        <div className="border border-[#1c332a] bg-[#080f0c] p-6 md:p-8">
          <p className="text-[11px] uppercase tracking-[0.25em] text-gold">Safe to spend</p>
          <p className="mt-3 font-display text-5xl tabular text-[#f4f7f5]">₦548,000</p>
          <p className="mt-2 text-sm text-[#7f9a8e]">
            Not your bank balance — what you can spend without breaking commitments.
          </p>
          <div className="gold-rule my-6" />
          <dl className="space-y-3 text-sm">
            <Row label="Income" value="₦2,000,000" />
            <Row label="Commitments" value="− ₦650,000" muted />
            <Row label="Protection" value="− ₦150,000" muted />
            <Row label="Wealth building" value="− ₦200,000" muted />
            <Row label="Buffer" value="− ₦90,000" muted />
          </dl>
          <p className="mt-6 text-xs uppercase tracking-[0.2em] text-[#7f9a8e]">
            IPÌLẸ̀ knows the difference
          </p>
        </div>
      </section>

      <section className="border-t border-[#1c332a] bg-[#070b09] px-6 py-16 md:px-10">
        <div className="mx-auto max-w-6xl">
          <p className="text-xs uppercase tracking-[0.28em] text-gold">One foundation</p>
          <h2 className="mt-3 max-w-2xl font-display text-3xl text-[#f4f7f5] md:text-4xl">
            Everything your family needs to build financial stability.
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Pillar
              title="Know your money"
              body="Accounts, income, transactions and cash flow — where money lives and moves."
            />
            <Pillar
              title="Plan what matters"
              body="Budgets, obligations, bills and sinking funds — prepare before due dates arrive."
            />
            <Pillar
              title="Build your wealth"
              body="Savings, investments, goals, assets and net worth — growth you can see."
            />
            <Pillar
              title="Make better decisions"
              body="Safe to Spend, simulations and insights — intelligence on verified numbers."
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16 md:px-10">
        <div className="grid gap-10 md:grid-cols-2 md:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-gold">Family</p>
            <h2 className="mt-3 font-display text-3xl text-[#f4f7f5] md:text-4xl">
              Money is personal.
              <br />
              Financial life is shared.
            </h2>
            <p className="mt-4 text-[#9fb8ad]">
              IPÌLẸ̀ gives households a shared view of the money, commitments and goals that matter
              most — partners, dependants, obligations and the future you&apos;re building together.
            </p>
          </div>
          <div className="border border-[#1c332a] bg-[#080f0c] p-6 font-display text-xl text-[#c8d9d0]">
            <p className="text-gold">You</p>
            <ul className="mt-4 space-y-2 border-l border-gold/40 pl-4 text-base text-[#9fb8ad]">
              <li>Partner</li>
              <li>Children &amp; dependants</li>
              <li>Family obligations</li>
              <li>Family goals</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="border-t border-[#1c332a] px-6 py-16 text-center md:px-10">
        <div className="mx-auto max-w-2xl">
          <div className="mx-auto flex max-w-xs flex-col items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-[#7f9a8e]">
            <span>Legacy</span>
            <span className="text-gold/70">↑</span>
            <span>Wealth</span>
            <span className="text-gold/70">↑</span>
            <span>Protection</span>
            <span className="text-gold/70">↑</span>
            <span>Planning</span>
            <span className="text-gold/70">↑</span>
            <span className="font-display text-lg tracking-[0.18em] text-gold">Foundation</span>
            <span className="text-gold/70">↑</span>
            <span className="font-display text-2xl tracking-[0.14em] text-[#c8d9d0]">IPÌLẸ̀</span>
          </div>
          <p className="mt-8 text-sm text-[#9fb8ad]">
            You don&apos;t just create an account. You build your financial foundation.
          </p>
          <Link
            href="/get-started"
            className="mt-6 inline-block bg-gold px-6 py-3 text-sm font-medium text-brand hover:bg-gold-bright"
          >
            Build your foundation →
          </Link>
        </div>
      </section>

      <footer className="border-t border-[#1c332a] px-6 py-8 md:px-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-[11px] uppercase tracking-[0.22em] text-[#7f9a8e] md:flex-row">
          <Wordmark tone="dark" size="sm" />
          <p>
            Money <span className="text-gold">·</span> Family <span className="text-gold">·</span> A
            brighter tomorrow
          </p>
        </div>
      </footer>
    </main>
  );
}

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-[#7f9a8e]">{label}</dt>
      <dd className={`tabular ${muted ? "text-[#9fb8ad]" : "text-[#f4f7f5]"}`}>{value}</dd>
    </div>
  );
}

function Pillar({ title, body }: { title: string; body: string }) {
  return (
    <article className="border border-[#1c332a] bg-[#080f0c] p-5">
      <h3 className="font-display text-xl text-[#f4f7f5]">{title}</h3>
      <p className="mt-3 text-sm leading-relaxed text-[#9fb8ad]">{body}</p>
    </article>
  );
}
