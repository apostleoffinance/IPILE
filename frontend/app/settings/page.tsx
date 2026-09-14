"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/shared/AppShell";
import { ConfirmationDialog } from "@/components/shared/ConfirmationDialog";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import {
  changeBillingPlan,
  createInvite,
  createSupportTicket,
  deleteCurrentHousehold,
  exportHousehold,
  getBilling,
  listInvites,
  listSupportTickets,
  revokeInvite,
  setHouseholdId,
  type Billing,
  type Invite,
  type SupportTicket,
} from "@/lib/api";

export default function SettingsPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [billing, setBilling] = useState<Billing | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("partner");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [ready, setReady] = useState(false);

  async function refresh() {
    const [nextBilling, nextInvites, nextTickets] = await Promise.all([
      getBilling(),
      listInvites().catch(() => [] as Invite[]),
      listSupportTickets(),
    ]);
    setBilling(nextBilling);
    setInvites(nextInvites);
    setTickets(nextTickets);
  }

  useEffect(() => {
    refresh()
      .then(() => setReady(true))
      .catch((err: Error) => {
        setError(err.message);
        setReady(true);
      });
  }, []);

  async function onExport() {
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const payload = await exportHousehold();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `family-os-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Export downloaded. The action was audited.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setPending(false);
    }
  }

  async function onDelete() {
    setPending(true);
    setError(null);
    try {
      await deleteCurrentHousehold();
      setHouseholdId(undefined);
      window.localStorage.removeItem("ffos_household_id");
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
      setPending(false);
      setConfirmDelete(false);
    }
  }

  async function onInvite(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createInvite({ email: inviteEmail, role: inviteRole });
      setInviteEmail("");
      setMessage("Invite created. Share the token with the invitee.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed.");
    } finally {
      setPending(false);
    }
  }

  async function onSupport(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createSupportTicket({ subject, body });
      setSubject("");
      setBody("");
      setMessage("Support ticket opened.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open ticket.");
    } finally {
      setPending(false);
    }
  }

  if (!ready) {
    return (
      <AppShell>
        <LoadingState />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-10 pb-16">
        <div>
          <p className="text-sm text-muted">Household & data rights</p>
          <h1 className="mt-1 text-3xl font-medium">Settings</h1>
        </div>
        {error ? <ErrorState message={error} /> : null}
        {message ? <p className="text-sm text-muted">{message}</p> : null}

        <section className="max-w-xl space-y-3">
          <h2 className="text-lg font-medium">Billing</h2>
          {billing ? (
            <>
              <p className="text-sm text-muted">
                Plan: {billing.plan_name} · {billing.currency} {billing.price_monthly}/mo ·{" "}
                {billing.billing_status}
              </p>
              <div className="flex flex-wrap gap-2">
                {billing.plans.map((plan) => (
                  <button
                    key={plan.id}
                    type="button"
                    disabled={pending || plan.id === billing.plan}
                    className="border border-line px-3 py-1.5 text-sm disabled:opacity-50"
                    onClick={async () => {
                      setPending(true);
                      try {
                        setBilling(await changeBillingPlan(plan.id));
                        setMessage(`Plan set to ${plan.name}.`);
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Billing update failed.");
                      } finally {
                        setPending(false);
                      }
                    }}
                  >
                    {plan.name}
                  </button>
                ))}
              </div>
            </>
          ) : null}
        </section>

        <section className="max-w-xl space-y-3">
          <h2 className="text-lg font-medium">Invites</h2>
          <form className="space-y-3" onSubmit={onInvite}>
            <label className="block text-sm">
              Email
              <input
                type="email"
                className="mt-1 w-full border border-line bg-surface px-3 py-2"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Role
              <select
                className="mt-1 w-full border border-line bg-surface px-3 py-2"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="partner">Partner</option>
                <option value="member">Member</option>
                <option value="viewer">Viewer</option>
              </select>
            </label>
            <button
              type="submit"
              disabled={pending}
              className="bg-ink px-4 py-2 text-sm text-surface disabled:opacity-50"
            >
              Create invite
            </button>
          </form>
          <ul className="space-y-2 text-sm">
            {invites.map((invite) => (
              <li key={invite.id} className="border border-line px-3 py-2">
                <p>
                  {invite.email} · {invite.role}
                </p>
                <p className="mt-1 break-all font-mono text-xs text-muted">{invite.token}</p>
                <button
                  type="button"
                  className="mt-2 text-xs underline"
                  onClick={async () => {
                    await revokeInvite(invite.id);
                    await refresh();
                  }}
                >
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="max-w-xl space-y-3">
          <h2 className="text-lg font-medium">Support</h2>
          <form className="space-y-3" onSubmit={onSupport}>
            <label className="block text-sm">
              Subject
              <input
                className="mt-1 w-full border border-line bg-surface px-3 py-2"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Message
              <textarea
                className="mt-1 min-h-24 w-full border border-line bg-surface px-3 py-2"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
              />
            </label>
            <button
              type="submit"
              disabled={pending}
              className="border border-line px-4 py-2 text-sm disabled:opacity-50"
            >
              Open ticket
            </button>
          </form>
          <ul className="space-y-2 text-sm text-muted">
            {tickets.map((ticket) => (
              <li key={ticket.id}>
                {ticket.status}: {ticket.subject}
              </li>
            ))}
          </ul>
        </section>

        <section className="max-w-xl space-y-3">
          <h2 className="text-lg font-medium">Export household</h2>
          <button
            type="button"
            disabled={pending}
            className="bg-ink px-4 py-2 text-sm text-surface disabled:opacity-50"
            onClick={onExport}
          >
            Download export
          </button>
        </section>

        <section className="max-w-xl space-y-3">
          <h2 className="text-lg font-medium">Delete household</h2>
          <p className="text-sm text-muted">
            Soft-deletes this household. You can create another from onboarding. Seed households are
            not recreated after delete.
          </p>
          <button
            type="button"
            disabled={pending}
            className="border border-line px-4 py-2 text-sm disabled:opacity-50"
            onClick={() => setConfirmDelete(true)}
          >
            Delete current household
          </button>
        </section>
      </div>
      {confirmDelete ? (
        <ConfirmationDialog
          title="Delete this household?"
          body="Members lose access immediately. Export first if you need a copy."
          confirmLabel="Delete household"
          onClose={() => setConfirmDelete(false)}
          onConfirm={onDelete}
        />
      ) : null}
    </AppShell>
  );
}
