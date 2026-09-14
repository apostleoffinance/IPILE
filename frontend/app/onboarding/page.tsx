"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  acceptInvite,
  api,
  createGoal,
  createInvite,
  getAccounts,
  onboardHousehold,
  setHouseholdId,
} from "@/lib/api";

const STEPS = [
  { label: "Welcome", title: "Welcome to IPÌLẸ̀.", body: "Let's build your household's financial foundation." },
  { label: "Together", title: "Who are you building this with?", body: "You can invite others later." },
  { label: "Income", title: "What does your household earn?", body: "We'll refine amounts on Home." },
  { label: "Money", title: "Where does your money live?", body: "Start with one account — add more anytime." },
  { label: "Prepare", title: "What must your household prepare for?", body: "Rent, school fees, debt, family support…" },
  { label: "Build", title: "What are you building toward?", body: "Emergency fund, home, education, investments…" },
  { label: "Ready", title: "Your foundation is taking shape.", body: "IPÌLẸ̀ will keep asking: Are we okay? What needs attention? What's next?" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [shape, setShape] = useState("couple");
  const [householdName, setHouseholdName] = useState("");
  const [partnerEmail, setPartnerEmail] = useState("");
  const [incomeHint, setIncomeHint] = useState("salary");
  const [accountName, setAccountName] = useState("Household current");
  const [accountBalance, setAccountBalance] = useState("0.00");
  const [obligationName, setObligationName] = useState("");
  const [goalName, setGoalName] = useState("Emergency fund");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [ready, setReady] = useState(false);
  const [inviteTokenOut, setInviteTokenOut] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        const continueSetup = typeof window !== "undefined" && window.location.search.includes("continue=1");
        if (me.households && me.households.length > 0 && !continueSetup) {
          setHouseholdId(me.households[0].id);
          router.replace("/overview");
          return;
        }
        if (!householdName) setHouseholdName(`${me.display_name.split(" ")[0]}'s household`);
        if (me.households?.[0]) setHouseholdId(me.households[0].id);
        setReady(true);
      })
      .catch(() => router.replace("/login"));
  }, [router, householdName]);

  async function ensureHousehold() {
    const me = await api.me();
    if (me.households && me.households.length > 0) {
      setHouseholdId(me.households[0].id);
      return me.households[0];
    }
    const household = await onboardHousehold({ name: householdName || "My household" });
    setHouseholdId(household.id);
    window.localStorage.setItem("ffos_household_id", household.id);
    return household;
  }

  async function next(event?: FormEvent) {
    event?.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (step === 0) {
        await ensureHousehold();
      }
      if (step === 1 && partnerEmail.trim()) {
        await ensureHousehold();
        const invite = await createInvite({ email: partnerEmail.trim(), role: "partner" });
        setInviteTokenOut(invite.token);
      }
      if (step === 3) {
        await ensureHousehold();
        const accounts = await getAccounts();
        if (!accounts.length) {
          await api.createAccount({
            name: accountName,
            type: "bank",
            current_balance: accountBalance || "0.00",
          });
        }
      }
      if (step === 4 && obligationName.trim()) {
        await ensureHousehold();
        const due = new Date();
        due.setDate(due.getDate() + 30);
        await api.createObligation({
          name: obligationName.trim(),
          amount: "100000.00",
          frequency: "monthly",
          next_due_date: due.toISOString().slice(0, 10),
          priority: "high",
        });
      }
      if (step === 5 && goalName.trim()) {
        await ensureHousehold();
        const deadline = new Date();
        deadline.setFullYear(deadline.getFullYear() + 1);
        await createGoal({
          name: goalName.trim(),
          type: "emergency",
          target_amount: "500000.00",
          current_amount: "0.00",
          deadline: deadline.toISOString().slice(0, 10),
        });
      }
      if (step >= STEPS.length - 1) {
        router.replace("/overview");
        return;
      }
      setStep((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not continue.");
    } finally {
      setPending(false);
    }
  }

  async function joinInvite(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await acceptInvite(token.trim());
      const me = await api.me();
      const household = me.households?.[0];
      if (household) {
        setHouseholdId(household.id);
        window.localStorage.setItem("ffos_household_id", household.id);
      }
      router.replace("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invite.");
      setPending(false);
    }
  }

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas">
        <LoadingState />
      </main>
    );
  }

  const current = STEPS[step];

  return (
    <main className="mx-auto min-h-screen max-w-xl px-6 py-10">
      <Wordmark href="/" tone="light" size="sm" />
      <p className="mt-8 text-xs uppercase tracking-[0.2em] text-muted">
        Step {step + 1} of {STEPS.length} · {current.label}
      </p>
      <h1 className="mt-2 font-display text-4xl text-ink">{current.title}</h1>
      <p className="mt-3 text-sm text-muted">{current.body}</p>
      {step === 0 ? (
        <p className="mt-2 text-xs uppercase tracking-[0.18em] text-gold">~5 minutes to get started</p>
      ) : null}
      <div className="gold-rule mt-4 w-28" />
      {error ? (
        <div className="mt-4">
          <ErrorState message={error} />
        </div>
      ) : null}

      {step === 0 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          {(
            [
              ["solo", "Just me"],
              ["couple", "My partner"],
              ["multi", "My family"],
              ["other", "Our household"],
            ] as const
          ).map(([value, label]) => (
            <label key={value} className="flex items-center gap-3 border border-line bg-surface px-3 py-3 text-sm">
              <input
                type="radio"
                name="shape"
                checked={shape === value}
                onChange={() => setShape(value)}
              />
              {label}
            </label>
          ))}
          <label className="block text-sm">
            Household name
            <input
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={householdName}
              onChange={(e) => setHouseholdName(e.target.value)}
              required
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 1 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <p className="text-sm text-muted">Invite a partner now, or skip for later.</p>
          <label className="block text-sm">
            Partner email (optional)
            <input
              type="email"
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={partnerEmail}
              onChange={(e) => setPartnerEmail(e.target.value)}
            />
          </label>
          {inviteTokenOut ? (
            <p className="break-all border border-line bg-subtle px-3 py-2 font-mono text-xs">
              Invite token: {inviteTokenOut}
            </p>
          ) : null}
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 2 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          {["salary", "business", "freelance", "investments", "other"].map((value) => (
            <label key={value} className="flex items-center gap-3 border border-line bg-surface px-3 py-3 text-sm capitalize">
              <input
                type="radio"
                name="income"
                checked={incomeHint === value}
                onChange={() => setIncomeHint(value)}
              />
              {value}
            </label>
          ))}
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 3 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            Account name
            <input
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Current balance
            <input
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={accountBalance}
              onChange={(e) => setAccountBalance(e.target.value)}
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 4 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            First obligation (optional)
            <input
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              placeholder="Rent, school fees, family support…"
              value={obligationName}
              onChange={(e) => setObligationName(e.target.value)}
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 5 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            First goal
            <input
              className="mt-1 w-full border border-line bg-surface px-3 py-2"
              value={goalName}
              onChange={(e) => setGoalName(e.target.value)}
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 6 ? (
        <div className="mt-8 space-y-4">
          <p className="text-xs text-muted">
            You can refine income amounts, Money plan and more inside IPÌLẸ̀ whenever you&apos;re ready.
          </p>
          <button
            type="button"
            disabled={pending}
            className="bg-accent px-4 py-2.5 text-sm text-white disabled:opacity-50"
            onClick={() => next()}
          >
            Enter IPÌLẸ̀ →
          </button>
        </div>
      ) : null}

      <form onSubmit={joinInvite} className="mt-10 border border-line bg-surface p-5">
        <h2 className="font-display text-xl">Or join with an invite</h2>
        <input
          className="mt-3 w-full border border-line bg-canvas px-3 py-2 font-mono text-xs"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Invite token"
        />
        <button type="submit" className="mt-3 text-sm text-accent underline" disabled={pending}>
          Accept invite
        </button>
      </form>
    </main>
  );
}

function PrimaryButton({ children, pending }: { children: React.ReactNode; pending: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="bg-accent px-4 py-2.5 text-sm text-white disabled:opacity-50"
    >
      {pending ? "Working…" : children}
    </button>
  );
}
