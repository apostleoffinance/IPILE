"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { ErrorState } from "@/components/shared/ErrorState";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, setHouseholdId } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.login({ email, password });
      const me = await api.me();
      if (!me.households || me.households.length === 0) {
        router.replace("/onboarding");
        return;
      }
      setHouseholdId(me.households[0].id);
      window.localStorage.setItem("ffos_household_id", me.households[0].id);
      router.replace("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center bg-canvas px-6 py-12 text-ink">
      <div className="absolute right-6 top-6">
        <ThemeToggle />
      </div>
      <Wordmark size="lg" priority />
      <form onSubmit={onSubmit} className="mt-10 w-full max-w-sm space-y-4">
        <div className="text-center">
          <h1 className="font-display text-3xl text-ink">Welcome back</h1>
          <p className="mt-2 text-sm text-muted">Your family&apos;s financial foundation awaits.</p>
        </div>
        <label className="block text-sm text-muted">
          Email
          <Input
            type="email"
            className="mt-1 w-full border border-line bg-input px-3 py-2.5 text-ink outline-none focus:border-gold/50"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label className="block text-sm text-muted">
          Password
          <Input
            type="password"
            minLength={12}
            className="mt-1 w-full border border-line bg-input px-3 py-2.5 text-ink outline-none focus:border-gold/50"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error ? <ErrorState message={error} /> : null}
        <Button type="submit" disabled={pending} variant="gold" className="w-full">
          {pending ? "Signing in..." : "Sign in"}
        </Button>
        <p className="text-center text-sm text-muted">
          Don&apos;t have an account?{" "}
          <Link href="/get-started" className="text-gold hover:text-gold-bright">
            Get started
          </Link>
        </p>
        <p className="text-center">
          <Link href="/" className="text-xs text-muted hover:text-ink">
            ← Back to IPÌLẸ̀
          </Link>
        </p>
      </form>
    </main>
  );
}
