"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Wordmark } from "@/components/brand/Wordmark";

const features = [
  ["01 / SEE CLEARLY", "Understand your whole picture", "Bring household accounts and activity into a single, organised financial view."],
  ["02 / PLAN AHEAD", "Give every naira direction", "Plan budgets, upcoming obligations and savings goals with more confidence."],
  ["03 / MOVE TOGETHER", "Build better habits together", "Coordinate household responsibilities and make shared decisions with clarity."],
];

export function LandingMockup() {
  return (
    <main className="ipile-marketing min-h-screen">
      <header className="ipile-marketing-nav">
        <Link href="/" aria-label="IPÌLẸ̀ home"><Wordmark size="sm" priority /></Link>
        <nav aria-label="Main navigation">
          <a href="#how">How it works</a><a href="#platform">Platform</a><a href="#features">Features</a><a href="#about">Our approach</a>
        </nav>
        <div className="ipile-marketing-nav-actions">
          <Link href="/login" className="ipile-marketing-signin">Sign in</Link>
          <Link href="/get-started" className="ipile-marketing-pill">Get started <ArrowUpRight size={15} /></Link>
        </div>
        <details className="ipile-marketing-mobile-menu"><summary aria-label="Open navigation">☰</summary><nav><a href="#how">How it works</a><a href="#platform">Platform</a><a href="#features">Features</a><a href="#about">Our approach</a><Link href="/login">Sign in</Link><Link href="/get-started">Get started</Link></nav></details>
      </header>

      <section className="ipile-marketing-hero">
        <div className="ipile-marketing-hero-copy">
          <p className="ipile-marketing-eyebrow">A better way to manage money</p>
          <h1>Your money.<br /><em>In harmony.</em></h1>
          <p className="ipile-marketing-lead">A clearer picture of your household finances. Bring your accounts, spending, plans and people together in one considered space.</p>
          <div className="ipile-marketing-actions"><Link href="/get-started" className="ipile-marketing-pill">Discover IPÌLẸ̀ <ArrowUpRight size={16} /></Link><a href="#platform">Explore the platform ↓</a></div>
          <p className="ipile-marketing-note">Clarity for today · Confidence for tomorrow</p>
        </div>
        <div className="ipile-marketing-orbit" aria-hidden="true"><span className="orbit-a" /><span className="orbit-b" /><span className="orbit-line" /></div>
        <a className="ipile-marketing-scroll" href="#how">Scroll to explore</a>
      </section>

      <section className="ipile-marketing-section" id="how">
        <div className="ipile-marketing-intro">
          <div><p className="ipile-marketing-kicker">One view. More perspective.</p><h2>Make room for<br />better money decisions.</h2></div>
          <p>Your financial life is connected. Your tools should be too. IPÌLẸ̀ helps you understand what comes in, what goes out, what you are building, and what needs your attention.</p>
        </div>
        <div className="ipile-marketing-features" id="features">
          {features.map(([number,title,body]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{body}</p></article>)}
        </div>
      </section>

      <section className="ipile-marketing-preview" id="platform">
        <div className="ipile-marketing-preview-head"><div><p className="ipile-marketing-kicker">A calmer financial workspace</p><h2>Everything, in its place.</h2></div><p>A first look at the IPÌLẸ̀ household dashboard. The figures below are sample content for this design preview.</p></div>
        <div className="ipile-marketing-dashboard">
          <div className="dashboard-top"><strong>IPÌLẸ̀ <span>·</span></strong><small>Household workspace　⌄　　◉ Olu A.</small></div>
          <div className="dashboard-body"><aside><b>◫　Overview</b><span>▣　Money</span><span>▤　Planning</span><span>◇　Wealth</span><span>⌁　Insights</span><span>♧　Family</span><span className="settings">⚙　Settings</span></aside>
            <div className="dashboard-main"><h3>Your household, in balance.</h3><p className="dashboard-caption">A clear view of where your money stands · Sample dashboard</p>
              <div className="dashboard-metrics"><article><small>Household net worth</small><strong>₦24,850,000</strong><span>↗ 6.8% this month</span></article><article><small>Monthly income</small><strong>₦4,250,000</strong><span>↗ 3.6%</span></article><article><small>Monthly spending</small><strong>₦1,680,000</strong><span>On track</span></article></div>
              <div className="dashboard-lower"><article><h4>Cash flow · Last 6 months</h4><div className="dashboard-chart">{[54,68,61,79,72,91].map((height,i)=><i key={i} style={{height:height+"%"}} />)}</div><div className="dashboard-months"><span>JUN</span><span>JUL</span><span>AUG</span><span>SEP</span><span>OCT</span><span>NOV</span></div></article>
                <article><h4>Monthly plan</h4>{[["Housing",40],["Food & groceries",20],["Transport",12],["Other",28]].map(([label,value],i)=><div className="dashboard-budget" key={label as string}><div><span>{label}</span><b>{value}%</b></div><i><span style={{width:value+"%",background:i===1?"#c9a45c":i===2?"#8da994":i===3?"#b7b2a6":"#003d35"}} /></i></div>)}</article></div>
            </div>
          </div>
        </div>
      </section>

      <section className="ipile-marketing-split" id="about">
        <div className="ipile-marketing-visual"><div className="visual-glow" /><article><small>HOUSEHOLD OVERVIEW</small><strong>₦ 4,250,000</strong><small>Monthly household income</small><hr /><footer><span>IPÌLẸ̀ FINANCIAL SPACE</span><span>01 / 04</span></footer></article></div>
        <div className="ipile-marketing-split-copy"><p className="ipile-marketing-kicker">Designed around real life</p><h2>More than numbers.<br />A stronger foundation.</h2><p>From everyday spending to long-term goals, IPÌLẸ̀ gives your household the context to make thoughtful financial decisions. Less scattered information. More confidence in the next step.</p><Link href="/get-started" className="ipile-marketing-pill">Explore the experience <ArrowUpRight size={16} /></Link></div>
      </section>

      <section className="ipile-marketing-cta"><p className="ipile-marketing-kicker">Your next chapter starts here</p><h2>Bring your financial life into focus.</h2><p>A thoughtful space for your household to see clearly, plan confidently and move forward together.</p><Link href="/get-started" className="ipile-marketing-pill">Get to know IPÌLẸ̀ <ArrowUpRight size={16} /></Link></section>
      <footer className="ipile-marketing-footer"><div><Wordmark size="sm" /><small>Clarity for today. Confidence for tomorrow.</small></div><nav><a href="#how">How it works</a><a href="#platform">Platform</a><a href="#features">Features</a><a href="mailto:hello@ipile.app">Contact</a></nav><small>© 2026 IPÌLẸ̀. All rights reserved.</small></footer>
    </main>
  );
}
