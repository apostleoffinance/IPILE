"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import {
  DecisionSimulatorPreview,
  FamilySection,
  FinancialEcosystem,
  FinalCTA,
  FoundationJourney,
  FoundationPillars,
  LandingFooter,
  LandingNav,
  ProductPreview,
  SafeToSpendPreview,
  WealthSection,
} from "@/components/landing/LandingSections";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, setHouseholdId } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api.me().then((me) => {
      if (!me.households || me.households.length === 0) {
        router.replace("/onboarding");
        return;
      }
      setHouseholdId(me.households[0].id);
      router.replace("/overview");
    }).catch(() => setChecking(false));
  }, [router]);

  if (checking) return <main className="flex min-h-screen items-center justify-center bg-canvas text-muted"><LoadingState label="Opening IPÌLẸ̀" /></main>;

  return (
    <main className="min-h-screen overflow-hidden bg-canvas text-ink">
      <LandingNav />
      <section className="relative px-5 pb-20 pt-16 md:px-10 md:pb-28 md:pt-24">
        <div className="mx-auto grid max-w-7xl gap-16 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div className="landing-reveal">
            <p className="eyebrow text-gold">The financial foundation for households everywhere</p>
            <h1 className="mt-5 max-w-2xl font-display text-6xl leading-[0.94] text-ink md:text-8xl">Your family&apos;s money.<br /><span className="text-forest">One foundation.</span></h1>
            <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted">IPÌLẸ̀ brings your household&apos;s money, commitments, goals and wealth into one clear financial foundation.</p>
            <div className="mt-9 flex flex-wrap items-center gap-5"><a href="/get-started" className="bg-accent px-5 py-3.5 text-sm font-semibold text-inverse transition-colors hover:bg-accent-deep">Build your foundation <ArrowUpRight className="ml-1 inline h-4 w-4" aria-hidden="true" /></a><a href="#how-it-works" className="text-sm font-semibold text-forest underline underline-offset-4">See how it works <ArrowDown className="ml-1 inline h-4 w-4" aria-hidden="true" /></a></div>
            <div className="mt-16 border-t border-line pt-5"><p className="max-w-lg font-display text-2xl leading-snug text-ink md:text-3xl">Know where your money is. Know what it is committed to. Know what you can safely spend.</p></div>
          </div>
          <div className="landing-reveal landing-delay"><SafeToSpendPreview /></div>
        </div>
      </section>
      <FinancialEcosystem />
      <FoundationPillars />
      <FamilySection />
      <FoundationJourney />
      <ProductPreview />
      <DecisionSimulatorPreview />
      <WealthSection />
      <FinalCTA />
      <LandingFooter />
    </main>
  );
}