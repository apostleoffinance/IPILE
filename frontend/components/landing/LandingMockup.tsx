"use client";

import Link from "next/link";
import { ArrowDown, ArrowUpRight, Check } from "lucide-react";
import { Wordmark } from "@/components/brand/Wordmark";

const audiences = [
  { title: "For individuals", body: "Bring your accounts, income, expenses, savings and ambitions together. Understand your finances and take control of your next decision." },
  { title: "For households", body: "Coordinate shared finances, household expenses, recurring obligations and financial priorities. Give everyone a clearer picture of what needs to be managed." },
  { title: "For families", body: "Bring family responsibilities, dependants, contributions, shared goals and long-term plans into one financial foundation." },
];

const foundations = [
  ["01", "Money clarity", "Know what you have, where it lives and how it moves."],
  ["02", "Planning", "Give your spending, bills and commitments a place in the bigger picture."],
  ["03", "Protection", "Prepare for obligations, build financial resilience and understand what is available after commitments."],
  ["04", "Wealth", "Turn consistent financial decisions into savings, investments and growing net worth."],
  ["05", "Legacy", "Build financial habits, stability and a foundation that can support the next season of life."],
];

const responsibilities = [
  "You and your personal finances",
  "Partners and shared responsibilities",
  "Children and dependants",
  "Family obligations and contributions",
  "Shared financial goals",
  "The future you are building",
];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="ipile-marketing-kicker">{children}</p>;
}

function SectionHeading({ label, title, body }: { label: string; title: string; body?: string }) {
  return (
    <div className="max-w-2xl">
      <SectionLabel>{label}</SectionLabel>
      <h2 className="mt-4 font-display text-4xl leading-tight tracking-tight text-[#050807] md:text-5xl">{title}</h2>
      {body ? <p className="mt-5 text-base leading-8 text-[#737973]">{body}</p> : null}
    </div>
  );
}

function PrimaryLink({ children = "Build your financial foundation", href = "/get-started" }: { children?: React.ReactNode; href?: string }) {
  return <Link href={href} className="ipile-marketing-pill">{children}<ArrowUpRight size={16} aria-hidden="true" /></Link>;
}

export function LandingMockup() {
  return (
    <main className="ipile-marketing min-h-screen">
      <header className="ipile-marketing-nav">
        <Link href="/" aria-label="IPÌLẸ̀ home"><Wordmark size="sm" priority /></Link>
        <nav aria-label="Main navigation">
          <a href="#foundation">Platform</a><a href="#who-its-for">Who it is for</a><a href="#family">Shared finances</a><a href="#preview">Product preview</a>
        </nav>
        <div className="ipile-marketing-nav-actions">
          <Link href="/login" className="ipile-marketing-signin">Sign in</Link>
          <PrimaryLink>Get started</PrimaryLink>
        </div>
        <details className="ipile-marketing-mobile-menu">
          <summary aria-label="Open navigation">☰</summary>
          <nav><a href="#foundation">Platform</a><a href="#who-its-for">Who it is for</a><a href="#family">Shared finances</a><a href="#preview">Product preview</a><Link href="/login">Sign in</Link><Link href="/get-started">Get started</Link></nav>
        </details>
      </header>

      <section className="ipile-marketing-hero">
        <div className="ipile-marketing-hero-copy">
          <p className="ipile-marketing-eyebrow">Your financial life, in one clear picture</p>
          <h1>Bring your financial life<br /><em>into focus.</em></h1>
          <p className="ipile-marketing-lead max-w-3xl">IPÌLẸ̀ brings your money, accounts, spending, commitments, plans and wealth together in one considered space — helping individuals, households and families understand where they stand and make more confident financial decisions.</p>
          <div className="ipile-marketing-actions">
            <PrimaryLink />
            <a href="#how-it-works">See how it works <ArrowDown className="inline h-4 w-4" aria-hidden="true" /></a>
          </div>
          <p className="ipile-marketing-hero-proof">Know what you have. Know what it is committed to. Know what you can safely spend. See what you are building towards.</p>
          <p className="ipile-marketing-note">Your money. In harmony.</p>
        </div>
        <div className="ipile-marketing-orbit" aria-hidden="true"><span className="orbit-a" /><span className="orbit-b" /><span className="orbit-line" /></div>
        <a className="ipile-marketing-scroll" href="#how-it-works">Scroll to explore</a>
      </section>

      <section className="ipile-marketing-section" id="how-it-works">
        <div className="ipile-marketing-intro">
          <div><SectionLabel>The whole picture</SectionLabel><h2>Your financial life is connected.<br />Your money shouldn&apos;t feel scattered.</h2></div>

        </div>
        <div className="ipile-marketing-features" id="whole-picture">
          {["Accounts", "Income", "Spending", "Commitments", "Savings", "Investments", "Family", "Goals"].map((item, index) => <article key={item}><span>0{index + 1}</span><h3>{item}</h3></article>)}
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28" id="foundation">
        <div className="mx-auto max-w-7xl">
          <SectionHeading label="One financial foundation" title="Everything you need to understand, plan and build your financial future." />
          <div className="mt-14 grid gap-px border border-[#dcded8] bg-[#dcded8] md:grid-cols-2">
            {[
              ["01", "Know your money", "Accounts, income, transactions and cash flow. Understand where your money lives, where it goes and how it moves."],
              ["02", "Plan what matters", "Budgets, bills, recurring expenses, obligations and sinking funds. Prepare for commitments before they become urgent."],
              ["03", "Build your wealth", "Savings, investments, financial goals, assets and net worth. Track your progress and build towards the future you want."],
              ["04", "Make better decisions", "Safe to Spend, financial simulations, insights and reports. Understand the consequences of financial decisions using your financial picture."],
            ].map(([number, title, body]) => <article key={number} className="bg-[#f7f6f2] p-7 md:p-10">
              <span className="text-xs font-semibold tracking-[.2em] text-[#b28c4b]">{number}</span><h3 className="mt-5 font-display text-3xl text-[#050807]">{title}</h3><p className="mt-4 max-w-md text-sm leading-7 text-[#737973]">{body}</p>
            </article>)}
          </div>
          <div className="mt-9"><PrimaryLink>Explore the platform</PrimaryLink></div>
        </div>
      </section>

      <section className="ipile-marketing-section" id="who-its-for">
        <div className="ipile-marketing-intro">
          <div><SectionLabel>Built around real financial life</SectionLabel><h2>Your finances are personal. Your financial responsibilities are unique.</h2></div>

        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {audiences.map((item, index) => <article key={item.title} className="border-t-2 border-[#003d35] bg-white/60 p-6 md:p-8"><span className="text-xs tracking-[.2em] text-[#b28c4b]">0{index + 1}</span><h3 className="mt-7 font-display text-3xl text-[#050807]">{item.title}</h3><p className="mt-4 text-sm leading-7 text-[#737973]">{item.body}</p></article>)}
        </div>
        <p className="mt-12 text-center font-display text-2xl text-[#003d35]">One platform. Different financial lives. A clearer picture for everyone.</p>
      </section>

      <section className="ipile-marketing-split" id="family">
        <div className="ipile-marketing-visual"><div className="visual-glow" /><article><small>THE PEOPLE BEHIND THE NUMBERS</small><strong>Money is personal.</strong><small>Financial life can be shared.</small><hr /><footer><span>IPÌLẸ̀ FINANCIAL FOUNDATION</span><span>02 / 05</span></footer></article></div>
        <div className="ipile-marketing-split-copy">
          <SectionLabel>The people behind the numbers</SectionLabel>
          <h2>Money is personal.<br />Financial life can be shared.</h2>
          <ul className="mt-6 space-y-3 text-sm text-[#505750]">{responsibilities.map((item) => <li key={item} className="flex items-center gap-3"><Check size={16} className="text-[#003d35]" aria-hidden="true" />{item}</li>)}</ul>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28">
        <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[.8fr_1.2fr]">
          <SectionHeading label="Underneath it all" title="A clearer foundation for every stage of your financial life." />
          <div className="border-t border-[#dcded8]">{foundations.map(([number, title, body]) => <article key={number} className="grid grid-cols-[42px_1fr] gap-4 border-b border-[#dcded8] py-6"><span className="pt-1 text-xs tracking-[.18em] text-[#b28c4b]">{number}</span><div><h3 className="font-display text-2xl text-[#050807]">{title}</h3><p className="mt-2 max-w-lg text-sm leading-7 text-[#737973]">{body}</p></div></article>)}</div>
        </div>
      </section>

      <section className="ipile-marketing-preview" id="preview">
        <div className="ipile-marketing-preview-head"><div><SectionLabel>A window into IPÌLẸ̀</SectionLabel><h2>See your financial picture clearly.</h2></div></div>
        <div className="ipile-marketing-dashboard">
          <div className="dashboard-top"><strong>IPÌLẸ̀ <span>·</span></strong><small>Household workspace　⌄　　◉ Sample profile</small></div>
          <div className="dashboard-body"><aside><b>◫　Overview</b><span>▣　Money</span><span>▤　Planning</span><span>◇　Wealth</span><span>⌁　Insights</span><span>♧　Family</span><span className="settings">⚙　Settings</span></aside>
            <div className="dashboard-main">
              <h3>Good morning.</h3><p className="dashboard-caption">Your financial overview · Illustrative product preview</p>
              <div className="dashboard-overview-grid">
                <article className="dashboard-safe-spend"><small>SAFE TO SPEND</small><strong>₦548,000</strong><p>Available after planned commitments, protection and wealth allocations.</p><div className="dashboard-safe-meta"><span>Monthly income</span><b>₦2.0M</b><span>Committed</span><b>₦1.1M</b></div></article>
                <div className="dashboard-stat-grid">
                  {[["Financial health","82 / 100","On a strong track"],["Net worth","₦4.8M","+8.4% this year"],["Emergency fund","₦900K","3.2 months covered"],["Investments","₦2.1M","Across 4 assets"]].map(([label,value,note]) => <article key={label}><small>{label}</small><strong>{value}</strong><span>{note}</span></article>)}
                </div>
              </div>
              <div className="dashboard-insights-grid">
                <article className="dashboard-panel dashboard-cashflow">
                  <div className="dashboard-panel-heading"><div><h4>Cash flow</h4><p>Income and spending over 6 months</p></div><span>Last 6 months</span></div>
                  <div className="dashboard-chart-wrap">
                    <div className="dashboard-y-labels"><span>₦2.0M</span><span>₦1.0M</span><span>₦0</span></div>
                    <svg viewBox="0 0 600 170" role="img" aria-label="Illustrative six-month cash flow trend showing income above spending" preserveAspectRatio="none">
                      <defs><linearGradient id="cashflow-area" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#0b6556" stopOpacity=".2"/><stop offset="100%" stopColor="#0b6556" stopOpacity="0"/></linearGradient></defs>
                      <path d="M0 42 L120 35 L240 54 L360 28 L480 40 L600 18 L600 160 L0 160 Z" fill="url(#cashflow-area)"/>
                      <path d="M0 42 L120 35 L240 54 L360 28 L480 40 L600 18" fill="none" stroke="#0b6556" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M0 112 L120 103 L240 118 L360 95 L480 108 L600 88" fill="none" stroke="#c9a45c" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                      {[0,120,240,360,480,600].map((x,i)=><g key={x}><circle cx={x} cy={[42,35,54,28,40,18][i]} r="4" fill="#0b6556"/><circle cx={x} cy={[112,103,118,95,108,88][i]} r="4" fill="#c9a45c"/></g>)}
                    </svg>
                  </div>
                  <div className="dashboard-chart-months"><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct</span><span>Nov</span></div>
                  <div className="dashboard-chart-legend"><span><i className="income-dot"/>Income</span><span><i className="spend-dot"/>Spending</span></div>
                </article>
                <article className="dashboard-panel dashboard-spending">
                  <div className="dashboard-panel-heading"><div><h4>Spending breakdown</h4><p>This month by category</p></div><span>₦620K total</span></div>
                  {[["Housing","₦220K",82],["Food","₦145K",62],["Transport","₦90K",42],["Family","₦85K",38],["Lifestyle","₦80K",34]].map(([label,value,width])=><div className="dashboard-spend-row" key={label}><div><span>{label}</span><b>{value}</b></div><i><span style={{width:width+"%"}}/></i></div>)}
                </article>
              </div>
              <div className="dashboard-lower">
                <article><div className="dashboard-panel-heading"><div><h4>Upcoming obligations</h4><p>Plan ahead for what is due</p></div><span>View plan ↗</span></div>{[["University fees","Due in 18 days","₦450,000"],["Parents’ rent","Due in 42 days","₦320,000"],["Utilities","Due in 7 days","₦65,000"]].map(([label,value,amount])=><div className="dashboard-obligation" key={label}><div><span>{label}</span><small>{value}</small></div><b>{amount}</b></div>)}</article>
                <article><div className="dashboard-panel-heading"><div><h4>Goals & attention</h4><p>What needs your attention</p></div><span>2 on track</span></div><div className="dashboard-goal"><div><span>Relocation fund</span><b>68%</b></div><i><span style={{width:"68%"}}/></i><small>₦1.36M of ₦2.0M target</small></div><div className="dashboard-goal"><div><span>Emergency fund</span><b>75%</b></div><i><span style={{width:"75%"}}/></i><small>Food spending is approaching its budget</small></div></article>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-20 md:px-12 md:py-28" id="decision-support">
        <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[1fr_.9fr] lg:items-center">
          <div><SectionLabel>Decision support</SectionLabel><h2 className="mt-4 max-w-xl font-display text-4xl leading-tight text-[#050807] md:text-5xl">Before you make a financial decision, understand what it changes.</h2>
            <p className="mt-6 max-w-xl text-base leading-8 text-[#737973]">Explore how changes in income and commitments could affect your plans before you decide.</p>
            <p className="mt-5 font-medium text-[#003d35]">Explore the possibilities before making the decision.</p>
          </div>
          <div className="border border-[#dcded8] bg-white p-6 md:p-8"><div className="flex items-center justify-between"><SectionLabel>Illustrative scenario</SectionLabel><span className="text-xs text-[#b28c4b]">What if?</span></div>
            <h3 className="mt-6 font-display text-3xl text-[#050807]">What if your income drops by 20%?</h3>
            <div className="mt-6 grid grid-cols-2 gap-3"><article className="bg-[#f7f6f2] p-4"><small className="text-[#737973]">Current monthly income</small><strong className="mt-2 block text-2xl">₦2.0M</strong></article><article className="bg-[#f7f6f2] p-4"><small className="text-[#737973]">Projected monthly income</small><strong className="mt-2 block text-2xl">₦1.6M</strong></article></div>
            <div className="mt-6 space-y-4 border-t border-[#e2e3de] pt-5 text-sm">{[["Safe to Spend","Recalculated"],["Emergency fund","Protection priorities maintained in the scenario"],["Financial goals","Timeline may need adjustment"],["Surplus","Reassessed against new income"]].map(([label,value]) => <div key={label} className="flex items-start justify-between gap-4"><span className="text-[#737973]">{label}</span><span className="max-w-[60%] text-right text-[#050807]">{value}</span></div>)}</div>
          </div>
        </div>
        <div className="mx-auto mt-10 max-w-7xl"><PrimaryLink>Explore the foundation</PrimaryLink></div>
      </section>

      <section className="ipile-marketing-cta">
        <div className="ipile-marketing-cta-inner">
          <p className="ipile-marketing-kicker">Your next chapter starts with clarity</p>
          <h2>A better understanding of your money starts here.</h2>
          <div className="ipile-marketing-cta-actions"><PrimaryLink>Build your financial foundation</PrimaryLink><Link href="#how-it-works" className="ipile-marketing-cta-secondary">See how IPÌLẸ̀ works <ArrowUpRight size={15} aria-hidden="true" /></Link></div>
          <p className="ipile-marketing-cta-brandline">Your money. In harmony.</p>
        </div>
      </section>
      <footer className="ipile-marketing-footer">
        <div><Wordmark size="sm" /><small>Clarity for today. Confidence for tomorrow.</small></div>
        <nav><a href="#foundation">Platform</a><a href="#who-its-for">Who it is for</a><a href="#family">Shared finances</a><a href="#preview">Product preview</a><Link href="/login">Sign in</Link><Link href="/get-started">Get started</Link></nav>
        <small>© 2026 IPÌLẸ̀. All rights reserved.</small>
      </footer>
    </main>
  );
}
