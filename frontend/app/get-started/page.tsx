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

export default function GetStartedPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.register({
        email,
        password,
        display_name: displayName,
        invite_token: inviteToken.trim() || undefined,
        create_household: !inviteToken.trim(),
      });
      const me = await api.me();
      if (!me.households || me.households.length === 0) {
        router.replace("/onboarding");
        return;
      }
      setHouseholdId(me.households[0].id);
      window.localStorage.setItem("ffos_household_id", me.households[0].id);
      router.replace("/onboarding?continue=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to continue.");
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
          <h1 className="font-display text-3xl text-ink">Build your foundation</h1>
          <p className="mt-2 text-sm text-muted">About five minutes to get started.</p>
        </div>
        <label className="block text-sm text-muted">
          Your name
          <Input
            className="mt-1 w-full border border-line bg-input px-3 py-2.5 text-ink outline-none focus:border-gold/50"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </label>
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
            autoComplete="new-password"
          />
        </label>
        <label className="block text-sm text-muted">
          Invite token <span className="opacity-70">(optional)</span>
          <Input
            className="mt-1 w-full border border-line bg-input px-3 py-2.5 font-mono text-xs text-ink outline-none focus:border-gold/50"
            value={inviteToken}
            onChange={(event) => setInviteToken(event.target.value)}
          />
        </label>
        {error ? <ErrorState message={error} /> : null}
        <Button type="submit" disabled={pending} variant="gold" className="w-full">
          {pending ? "Creating..." : "Continue →"}
        </Button>
        <p className="text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-gold hover:text-gold-bright">
            Sign in
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
