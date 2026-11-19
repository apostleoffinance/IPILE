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
          eyebrow="Support"
          title="Help"
          description="Simple guidance for managing your household finances with IPÌLẸ̀."
        />
        <section className="space-y-2 text-sm">
          <SectionHeader title="Get started" />
          <p className="text-muted">
            Add your accounts, record income and expenses, and set the priorities that matter to your household. Your Family Financial Constitution is simply your household money plan: the order in which income is shared across your priorities.
          </p>
        </section>
        <section className="space-y-2 text-sm">
          <SectionHeader title="Invites" />
          <p className="text-muted">
            Household owners can invite another person from Settings. Share the invitation code with them; they should accept it using the invited email address.
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
            Send us a support request from{" "}
            <Link className="underline" href="/settings">
              Settings
            </Link>
            . 
          </p>
        </section>
      </ContentContainer>
    </AppShell>
  );
}
