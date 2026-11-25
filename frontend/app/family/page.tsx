import Link from "next/link";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";

const areas = [
  { href: "/family/members", number: "01", title: "Household members", description: "Manage the people in your household, their roles and what they can access.", meta: "People & permissions" },
  { href: "/family/contributions", number: "02", title: "Contributions", description: "Set contribution agreements, follow schedules and record what has been received.", meta: "Agreements & records" },
  { href: "/family/giving", number: "03", title: "Giving", description: "Manage household giving policies, approvals and recorded gifts.", meta: "Policies & approvals" },
];

export default function FamilyPage() {
  return (
    <AppShell>
      <ContentContainer>
        <div className="ipile-workspace ipile-family-workspace">
          <PageHeader eyebrow="Household" title="Family" description="A shared view of the people, commitments and giving practices that shape your household." />
          <section className="ipile-workspace-intro">
            <p className="eyebrow">Household governance</p>
            <h2>Make the shared decisions visible.</h2>
            <p>Keep household membership, contribution expectations and giving practices organised in one considered space.</p>
          </section>
          <div className="ipile-workspace-grid">
            {areas.map((area) => (
              <Link key={area.href} href={area.href} className="ipile-workspace-card">
                <span className="ipile-workspace-card-number">{area.number}</span>
                <span className="ipile-workspace-card-meta">{area.meta}</span>
                <h2>{area.title}</h2>
                <p>{area.description}</p>
                <span className="ipile-workspace-card-link">Open workspace <span aria-hidden="true">↗</span></span>
              </Link>
            ))}
          </div>
        </div>
      </ContentContainer>
    </AppShell>
  );
}
