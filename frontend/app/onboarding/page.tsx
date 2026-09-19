"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Wordmark } from "@/components/brand/Wordmark";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  acceptInvite,
  api,
  createAllocationRule,
  createGoal,
  createInvite,
  getAccounts,
  getAllocationRules,
  onboardHousehold,
  setHouseholdId,
} from "@/lib/api";
import { moneyString } from "@/lib/forms";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";

const STEPS = [
  { label: "Welcome", title: "Welcome to IPÌLẸ̀.", body: "Let's build your household's financial foundation." },
  { label: "Together", title: "Who are you building this with?", body: "You can invite others later." },
  { label: "Income", title: "What does your household earn?", body: "A monthly figure helps IPÌLẸ̀ allocate with you." },
  { label: "Money", title: "Where does your money live?", body: "Start with one account. Add more anytime." },
  {
    label: "Priorities",
    title: "What should happen first when money comes in?",
    body: "Pick what matters. We'll start with a surplus rule you can refine later.",
  },
  { label: "Prepare", title: "What must your household prepare for?", body: "Rent, school fees, debt, family support..." },
  { label: "Build", title: "What are you building toward?", body: "Emergency fund, home, education, investments..." },
  { label: "Ready", title: "Your foundation is taking shape.", body: "IPÌLẸ̀ will keep asking: Are we okay? What needs attention? What's next?" },
];

const DESTINATION_OPTIONS = [
  { id: "giving", label: "Giving" },
  { id: "obligations", label: "Obligations" },
  { id: "essentials", label: "Essentials" },
  { id: "protection", label: "Protection / buffer" },
  { id: "goals", label: "Goals" },
  { id: "surplus", label: "Surplus / flexible" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [shape, setShape] = useState("couple");
  const [householdName, setHouseholdName] = useState("");
  const [partnerEmail, setPartnerEmail] = useState("");
  const [incomeHint, setIncomeHint] = useState("salary");
  const [incomeAmount, setIncomeAmount] = useState("");
  const [accountName, setAccountName] = useState("Household current");
  const [accountBalance, setAccountBalance] = useState("0.00");
  const [priorities, setPriorities] = useState<string[]>(["surplus"]);
  const [obligationName, setObligationName] = useState("");
  const [obligationAmount, setObligationAmount] = useState("");
  const [goalName, setGoalName] = useState("Emergency fund");
  const [goalTarget, setGoalTarget] = useState("");
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

  async function ensureIncomeSource() {
    if (!incomeAmount.trim()) return;
    const sources = await api.incomeSources();
    if (sources.length) return sources[0];
    return api.createIncomeSource({
      name: incomeHint.charAt(0).toUpperCase() + incomeHint.slice(1),
      expected_amount: incomeAmount,
      type: incomeHint,
    });
  }

  async function maybeRecordIncome() {
    if (!incomeAmount.trim()) return;
    const accounts = await getAccounts();
    if (!accounts.length) return;
    const source = await ensureIncomeSource();
    const existing = await api.income();
    if (existing.length) return;
    await api.recordIncome({
      account_id: accounts[0].id,
      amount: incomeAmount,
      date: new Date().toISOString().slice(0, 10),
      income_source_id: source?.id,
      description: "Onboarding income",
    });
  }

  function togglePriority(id: string) {
    setPriorities((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
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
      if (step === 2) {
        await ensureHousehold();
        await ensureIncomeSource();
        await maybeRecordIncome();
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
        await maybeRecordIncome();
      }
      if (step === 4) {
        await ensureHousehold();
        const rules = await getAllocationRules();
        if (!rules.some((rule) => rule.type === "remainder")) {
          await createAllocationRule({
            name: "Household surplus",
            type: "remainder",
            basis: "remaining",
            priority: 100,
            mandatory: false,
            destination_type: "account",
          });
        }
        // Priorities are captured conversationally; surplus remainder is the light stub.
        void priorities;
      }
      if (step === 5 && obligationName.trim() && obligationAmount.trim()) {
        if (!moneyString.safeParse(obligationAmount).success) throw new Error("Enter a valid obligation amount.");
        await ensureHousehold();
        const due = new Date();
        due.setDate(due.getDate() + 30);
        await api.createObligation({
          name: obligationName.trim(),
          amount: obligationAmount,
          frequency: "monthly",
          next_due_date: due.toISOString().slice(0, 10),
          priority: "high",
        });
      }
      if (step === 6 && goalName.trim() && goalTarget.trim()) {
        if (!moneyString.safeParse(goalTarget).success) throw new Error("Enter a valid goal target.");
        await ensureHousehold();
        const deadline = new Date();
        deadline.setFullYear(deadline.getFullYear() + 1);
        await createGoal({
          name: goalName.trim(),
          type: "emergency",
          target_amount: goalTarget,
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
      <main id="main-content" tabIndex={-1} className="flex min-h-screen items-center justify-center bg-canvas outline-none">
        <LoadingState />
      </main>
    );
  }

  const current = STEPS[step];

  return (
    <main id="main-content" tabIndex={-1} className="mx-auto min-h-screen max-w-xl px-6 py-10 outline-none">
      <Wordmark href="/" tone="light" size="sm" />
      <nav aria-label="Onboarding progress" className="mt-8">
        <p className="text-xs uppercase tracking-[0.2em] text-muted">
          Step {step + 1} of {STEPS.length} · {current.label}
        </p>
        <ol className="mt-3 flex gap-1" aria-hidden>
          {STEPS.map((row, index) => (
            <li
              key={row.label}
              className={`h-1 flex-1 ${index <= step ? "bg-accent" : "bg-subtle"}`}
            />
          ))}
        </ol>
      </nav>
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
            <Input
              className="mt-1"
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
            <Input
              type="email"
              className="mt-1"
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
          <label className="block text-sm">
            Typical monthly amount (optional)
            <Input
              className="mt-1"
              placeholder="e.g. 2000000.00"
              value={incomeAmount}
              onChange={(e) => setIncomeAmount(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 3 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            Account name
            <Input
              className="mt-1"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            Current balance
            <Input
              className="mt-1"
              value={accountBalance}
              onChange={(e) => setAccountBalance(e.target.value)}
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 4 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          {DESTINATION_OPTIONS.map((option) => (
            <label key={option.id} className="flex items-center gap-3 border border-line bg-surface px-3 py-3 text-sm">
              <Checkbox
                type="checkbox"
                checked={priorities.includes(option.id)}
                onChange={() => togglePriority(option.id)}
              />
              {option.label}
            </label>
          ))}
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 5 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            First obligation (optional)
            <Input
              className="mt-1"
              placeholder="Rent, school fees, family support..."
              value={obligationName}
              onChange={(e) => setObligationName(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Amount (optional)
            <Input
              className="mt-1"
              placeholder="150000.00"
              value={obligationAmount}
              onChange={(e) => setObligationAmount(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 6 ? (
        <form className="mt-8 space-y-4" onSubmit={next}>
          <label className="block text-sm">
            First goal
            <Input
              className="mt-1"
              value={goalName}
              onChange={(e) => setGoalName(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Target amount
            <Input
              className="mt-1"
              placeholder="500000.00"
              value={goalTarget}
              onChange={(e) => setGoalTarget(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <PrimaryButton pending={pending}>Continue →</PrimaryButton>
        </form>
      ) : null}

      {step === 7 ? (
        <div className="mt-8 space-y-4">
          <p className="text-xs text-muted">
            You can refine income amounts, Money plan and more inside IPÌLẸ̀ whenever you&apos;re ready.
          </p>
          <Button type="button" disabled={pending} onClick={() => next()}>
            Enter IPÌLẸ̀ →
          </Button>
        </div>
      ) : null}

      <form onSubmit={joinInvite} className="mt-10 border border-line bg-surface p-5">
        <h2 className="font-display text-xl">Or join with an invite</h2>
        <Input
          className="mt-3 font-mono text-xs"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Invite token"
        />
        <Button type="submit" variant="link" size="sm" className="mt-3" disabled={pending}>
          Accept invite
        </Button>
      </form>
    </main>
  );
}

function PrimaryButton({ children, pending }: { children: React.ReactNode; pending: boolean }) {
  return (
    <Button type="submit" disabled={pending}>
      {pending ? "Working..." : children}
    </Button>
  );
}
