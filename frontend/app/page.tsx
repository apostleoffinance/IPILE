"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight } from "lucide-react";
import { LoadingState } from "@/components/shared/LoadingState";
import { api, setHouseholdId } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api.me().then((me) => {
      if (!me.households || me.households.length === 0) {
        router.replace("/onboarding");
        return;
      }
      setHouseholdId(me.households[0].id);
      router.replace("/overview");
    }).catch(() => setChecking(false));
  }, [router]);

  useEffect(() => {
    if (checking) return;
    const nodes = document.querySelectorAll<HTMLElement>(".ipile-mock-reveal");
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [checking]);

  if (checking) return <main className="flex min-h-screen items-center justify-center bg-canvas text-muted"><LoadingState label="Opening IPÌLẸ̀" /></main>;

  return (
    <main className="ipile-mock-page">
      <header className="ipile-mock-nav">
        <a className="ipile-mock-logo" href="/" aria-label="IPÌLẸ̀ home">IPÌLẸ̀</a>
        <nav className={menuOpen ? "ipile-mock-links mobile-open" : "ipile-mock-links"} aria-label="Main navigation">
          <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#platform" onClick={() => setMenuOpen(false)}>Platform</a>
          <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
          <a href="#about" onClick={() => setMenuOpen(false)}>Our approach</a>
        </nav>
        <div className="ipile-mock-navright">
          <a className="ipile-mock-textlink" href="/login">Sign in</a>
          <a className="ipile-mock-pill" href="/get-started">Get started <ArrowUpRight aria-hidden="true" /></a>
        </div>
        <button className="ipile-mock-menu" type="button" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>{menuOpen ? "×" : "☰"}</button>
      </header>

      <section className="ipile-mock-hero">
        <div className="ipile-mock-hero-copy">
          <p className="ipile-mock-eyebrow">A better way to manage money</p>
          <h1>Your money.<br /><em>In harmony.</em></h1>
          <p className="ipile-mock-hero-sub">A clearer picture of your household finances. Bring your accounts, spending, plans and people together in one considered space.</p>
          <div className="ipile-mock-actions">
            <a className="ipile-mock-pill" href="/get-started">Discover IPÌLẸ̀ <ArrowUpRight aria-hidden="true" /></a>
            <a className="ipile-mock-textlink" href="#platform">Explore the platform ↓</a>
          </div>
          <p className="ipile-mock-note">Clarity for today · Confidence for tomorrow</p>
        </div>
        <div className="ipile-mock-orbit-stage" aria-hidden="true"><div className="ipile-mock-orbit top" /><div className="ipile-mock-orbit bottom" /><div className="ipile-mock-orbit-line" /></div>
        <a className="ipile-mock-scroll" href="#how">Scroll to explore</a>
      </section>

      <section className="ipile-mock-section" id="how">
        <div className="ipile-mock-intro-grid ipile-mock-reveal">
          <div><p className="ipile-mock-kicker">One view. More perspective.</p><h2>Make room for<br />better money decisions.</h2></div>
          <div className="right"><p>Your financial life is connected. Your tools should be too. IPÌLẸ̀ helps you understand what comes in, what goes out, what you are building, and what needs your attention.</p></div>
        </div>
        <div className="ipile-mock-feature-grid" id="features">
          <article className="ipile-mock-feature ipile-mock-reveal"><span>01 / SEE CLEARLY</span><h3>Understand your whole picture</h3><p>Bring household accounts and activity into a single, organised financial view.</p></article>
          <article className="ipile-mock-feature ipile-mock-reveal"><span>02 / PLAN AHEAD</span><h3>Give every naira direction</h3><p>Plan budgets, upcoming obligations and savings goals with more confidence.</p></article>
          <article className="ipile-mock-feature ipile-mock-reveal"><span>03 / MOVE TOGETHER</span><h3>Build better habits together</h3><p>Coordinate household responsibilities and make shared decisions with clarity.</p></article>
        </div>
      </section>

      <section className="ipile-mock-preview" id="platform">
        <div className="ipile-mock-preview-head ipile-mock-reveal">
          <div><p className="ipile-mock-kicker">A calmer financial workspace</p><h2>Everything, in its place.</h2></div>
          <p>A first look at the IPÌLẸ̀ household dashboard. The figures below are sample content for this design preview.</p>
        </div>
        <div className="ipile-mock-dashboard ipile-mock-reveal">
          <div className="ipile-mock-dash-top"><strong>IPÌLẸ̀ <span>·</span></strong><small>Household workspace　⌄　　◉ Olu A.</small></div>
          <div className="ipile-mock-dash-body">
            <aside><div className="active">◫　Overview</div><div>▣　Money</div><div>▤　Planning</div><div>◇　Wealth</div><div>⌁　Insights</div><div>♧　Family</div><div className="settings">⚙　Settings</div></aside>
            <div className="ipile-mock-dash-main">
              <h3>Your household, in balance.</h3><p className="caption">A clear view of where your money stands · Sample dashboard</p>
              <div className="ipile-mock-metrics">
                <div><small>Household net worth</small><strong>₦24,850,000</strong><span>↗ 6.8% this month</span></div>
                <div><small>Monthly income</small><strong>₦4,250,000</strong><span>↗ 3.6%</span></div>
                <div><small>Monthly spending</small><strong>₦1,680,000</strong><span>On track</span></div>
              </div>
              <div className="ipile-mock-dash-lower">
                <div className="ipile-mock-panel"><h4>Cash flow · Last 6 months</h4><div className="ipile-mock-chart">{[54,68,61,79,72,91].map((height,index)=><i key={index} style={{height:`${height}%`}} />)}</div><div className="ipile-mock-chart-labels">{["JUN","JUL","AUG","SEP","OCT","NOV"].map(x=><span key={x}>{x}</span>)}</div></div>
                <div className="ipile-mock-panel"><h4>Monthly plan</h4>{[["Housing","40%","40%",""],["Food & groceries","20%","20%","gold"],["Transport","12%","12%","sage"],["Other","28%","28%","stone"]].map(([label,value,width,tone])=><div className="ipile-mock-budget" key={label}><div><span>{label}</span><b>{value}</b></div><i className={tone} style={{width}} /></div>)}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="ipile-mock-section ipile-mock-feature-section" id="about">
        <div className="ipile-mock-split">
          <div className="ipile-mock-split-visual ipile-mock-reveal"><div className="ipile-mock-glow" /><div className="ipile-mock-floating-card"><small>HOUSEHOLD OVERVIEW</small><strong>₦ 4,250,000</strong><small>Monthly household income</small><hr /><footer><span>IPÌLẸ̀ FINANCIAL SPACE</span><span>01 / 04</span></footer></div></div>
          <div className="ipile-mock-split-copy ipile-mock-reveal"><p className="ipile-mock-kicker">Designed around real life</p><h2>More than numbers.<br />A stronger foundation.</h2><p>From everyday spending to long-term goals, IPÌLẸ̀ gives your household the context to make thoughtful financial decisions. Less scattered information. More confidence in the next step.</p><a className="ipile-mock-pill" href="/get-started">Explore the experience <ArrowUpRight aria-hidden="true" /></a></div>
        </div>
      </section>

      <section className="ipile-mock-dark-band" id="get-started">
        <p className="ipile-mock-kicker">Your next chapter starts here</p><h2>Bring your financial life into focus.</h2><p>A thoughtful space for your household to see clearly, plan confidently and move forward together.</p><a className="ipile-mock-pill" href="/get-started">Get to know IPÌLẸ̀ <ArrowUpRight aria-hidden="true" /></a>
      </section>
      <footer className="ipile-mock-footer"><div><strong>IPÌLẸ̀<span>·</span></strong><small>Clarity for today. Confidence for tomorrow.</small></div><nav><a href="#how">How it works</a><a href="#platform">Platform</a><a href="#features">Features</a><a href="mailto:hello@ipile.app">Contact</a></nav><small>© 2026 IPÌLẸ̀. All rights reserved.</small></footer>
    </main>
  );
}
