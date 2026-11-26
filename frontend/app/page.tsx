"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LandingMockup } from "@/components/landing/LandingMockup";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, setHouseholdId } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

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

  useEffect(() => {
    if (checking) return;
    const nodes = document.querySelectorAll<HTMLElement>(".ipile-mock-reveal");
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [checking]);

  if (checking) return <main className="flex min-h-screen items-center justify-center bg-canvas text-muted"><LoadingState label="Opening IPÌLẸ̀" /></main>;

  return <LandingMockup />;
}
