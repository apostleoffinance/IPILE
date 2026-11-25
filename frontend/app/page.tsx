"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
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
      <section className="ipile-landing-hero">
        <div className="ipile-hero-inner ipile-reveal">
          <p className="eyebrow ipile-hero-eyebrow">A better way to manage money</p>
          <h1>Your money.<br /><span>In harmony.</span></h1>
          <p className="ipile-hero-copy">A clearer picture of your household finances. Bring your accounts, spending, plans and people together in one considered space.</p>
          <div className="ipile-hero-actions flex flex-wrap items-center gap-5">
            <a href="/get-started" className="inline-flex items-center gap-3">Discover IPÌLẸ̀ <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></a>
            <a href="#how-it-works" className="text-sm font-medium text-forest">Explore the platform ↓</a>
          </div>
          <p className="mt-7 text-[9px] uppercase tracking-[0.2em] text-muted">Clarity for today · Confidence for tomorrow</p>
        </div>
        <div className="ipile-hero-scroll">Scroll to explore</div>
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