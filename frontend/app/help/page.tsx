"use client";

import Link from "next/link";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";

export default function HelpPage() {
  return (
    <AppShell>
      <ContentContainer className="max-w-2xl">
        <PageHeader
          eyebrow="IPÌLẸ̀ docs"
          title="Help"
          description="How the household financial OS fits together."
        />
        <section className="space-y-2 text-sm">
          <SectionHeader title="Get started" />
          <p className="text-muted">
            Get started, add an account, record income, then use Home for Safe to Spend and health. Your
            Family Financial Constitution is the ordered allocation rules and policies you configure.
            Engines stay universal.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <SectionHeader title="Invites" />
          <p className="text-muted">
            Owners create invites under Settings. Share the token; the invitee accepts with the same
            email.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <SectionHeader title="Billing" />
          <p className="text-muted">
            Pilot is free. Family is the public plan placeholder. Change plans under Settings → Billing.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <SectionHeader title="Support" />
          <p className="text-muted">
            Open a ticket from{" "}
            <Link className="underline" href="/settings">
              Settings
            </Link>
            . Full write-up lives in the repo at <code>docs/PUBLIC.md</code>.
          </p>
        </section>
      </ContentContainer>
    </AppShell>
  );
}
