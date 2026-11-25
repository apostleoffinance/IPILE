"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { LandingMockup } from "@/components/landing/LandingMockup";
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

  return <LandingMockup />;
}
