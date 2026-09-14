"use client";

import Link from "next/link";
import { AppShell } from "@/components/shared/AppShell";

export default function HelpPage() {
  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6 pb-16">
        <div>
          <p className="text-sm text-muted">IPÌLẸ̀ docs</p>
          <h1 className="mt-1 text-3xl font-medium">Help</h1>
        </div>
        <section className="space-y-2 text-sm">
          <h2 className="text-lg font-medium">Get started</h2>
          <p className="text-muted">
            Get started, add an account, record income, then use Home for Safe to Spend,
            and health. Your Family Financial Constitution is the ordered allocation rules and
            policies you configure — engines stay universal.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <h2 className="text-lg font-medium">Invites</h2>
          <p className="text-muted">
            Owners create invites under Settings. Share the token; the invitee accepts with the same
            email.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <h2 className="text-lg font-medium">Billing</h2>
          <p className="text-muted">
            Pilot is free. Family is the public plan placeholder. Change plans under Settings →
            Billing.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <h2 className="text-lg font-medium">Support</h2>
          <p className="text-muted">
            Open a ticket from{" "}
            <Link className="underline" href="/settings">
              Settings
            </Link>
            . Full write-up lives in the repo at <code>docs/PUBLIC.md</code>.
          </p>
        </section>
      </div>
    </AppShell>
  );
}
