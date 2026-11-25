"use client";
import { useEffect,useMemo,useState } from "react";
import Link from "next/link";
import { NetWorthChart } from "@/components/charts/NetWorthChart";
import { InsightsCashFlowChart } from "@/components/charts/InsightsCashFlowChart";
import { SpendCategoryChart } from "@/components/charts/SpendCategoryChart";
import { DecisionCard } from "@/components/financial/DecisionCard";
import { MoneyAmount } from "@/components/financial/MoneyAmount";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { SectionHeader } from "@/components/layouts/SectionHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Tabs,TabsContent,TabsList,TabsTrigger } from "@/components/ui/tabs";
import { explainWithAi,getInsights,type Insights } from "@/lib/api";
import { decisionHrefForPattern } from "@/lib/decision-routing";

export default function InsightsPage(){
 const [data,setData]=useState<Insights|null>(null),[error,setError]=useState<string|null>(null);
 const [explanation,setExplanation]=useState<string|null>(null),[pending,setPending]=useState(false),[refreshing,setRefreshing]=useState(false);
 async function refresh(){setRefreshing(true);setError(null);try{setData(await getInsights())}catch(err){setError(err instanceof Error?err.message:"Unable to load household insights.")}finally{setRefreshing(false)}}
 useEffect(()=>{let active=true;getInsights().then(value=>{if(active)setData(value)}).catch((err:Error)=>{if(active)setError(err.message)});return()=>{active=false}},[]);
 const currency=data?.currency??"NGN";
 const severity=useMemo(()=>(value:string)=>value==="critical"?"critical" as const:value==="warning"?"warning" as const:value==="info"?"info" as const:"neutral" as const,[]);
 return <AppShell>
  {!data&&!error?<LoadingState/>:null}
  {error&&!data?<ContentContainer><ErrorState message={error}/><Button type="button" variant="outline" onClick={refresh}>Try again</Button></ContentContainer>:null}
  {data?<ContentContainer className="ipile-insights-workspace">
   <PageHeader eyebrow="Household intelligence" title="Insights" description="Understand the patterns behind your household's money, see what is changing and decide what deserves attention." actions={<div className="flex flex-wrap gap-2"><Button type="button" variant="outline" disabled={refreshing} onClick={refresh}>{refreshing?"Refreshing…":"Refresh"}</Button><Link href="/reports" className="inline-flex min-h-10 items-center rounded-md border border-line px-4 text-sm font-medium text-ink hover:bg-subtle">View reports</Link></div>}/>
   <section className="ipile-insights-summary">
    <div><p className="ipile-insights-label">Financial health</p><p className="ipile-insights-score">{data.health?.score??"—"}<span>/100</span></p><p className="ipile-insights-note">{data.health?.label??"No health label available"}</p></div>
    <div><p className="ipile-insights-label">Reporting period</p><p className="ipile-insights-period">{data.period_start} — {data.period_end}</p><p className="ipile-insights-note">Based on recorded household activity</p></div>
    <div><p className="ipile-insights-label">Patterns to review</p><p className="ipile-insights-score">{data.patterns?.length??0}</p><p className="ipile-insights-note">Signals returned by the household insight engine</p></div>
   </section>
   <div className="ipile-insights-toolbar"><div><p className="ipile-insights-label">Your financial picture</p><p className="text-sm text-muted">Explore trends, spending behaviour and giving against household limits.</p></div><Button type="button" variant="outline" disabled={pending} onClick={async()=>{setPending(true);setError(null);try{setExplanation((await explainWithAi()).explanation)}catch(err){setError(err instanceof Error?err.message:"Unable to explain these insights.")}finally{setPending(false)}}}>{pending?"Preparing explanation…":"Explain with IPÌLẸ̀"}</Button></div>
   {explanation?<section className="ipile-insights-explanation"><p className="ipile-insights-label">AI explanation · verified household data</p><p className="mt-2 whitespace-pre-wrap text-sm leading-7">{explanation}</p></section>:null}
   {error?<ErrorState message={error}/>:null}
   <Tabs defaultValue="overview" className="ipile-insights-tabs">
    <TabsList><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="trends">Trends</TabsTrigger><TabsTrigger value="spending">Spending</TabsTrigger><TabsTrigger value="giving">Giving</TabsTrigger></TabsList>
    <TabsContent value="overview" className="space-y-7">
     <section><SectionHeader title="What needs attention" description="Signals produced from recorded household activity."/>
      {!data.patterns?.length?<EmptyState title="No patterns to review" body="Relevant changes and risks will appear here as household activity is recorded."/>:<div className="grid gap-3 lg:grid-cols-2">{data.patterns.map(p=><DecisionCard key={p.code+p.title} title={p.title} body={p.detail} href={decisionHrefForPattern(p.code)} severity={severity(p.severity)}/>)}</div>}
     </section>
     <section><SectionHeader title="Household cash flow" description="Income, expenses and surplus across saved reporting periods."/>
      {!data.cash_flow.length?<EmptyState title="Cash-flow history is not available yet" body="Period summaries will appear here when they have been saved."/>:<InsightsCashFlowChart points={data.cash_flow}/>}
     </section>
    </TabsContent>
    <TabsContent value="trends" className="space-y-7">
     <section><SectionHeader title="Net worth over time" description="Recorded household net-worth snapshots. No projections are shown here."/>
      {!data.net_worth.length?<EmptyState title="No net-worth history yet" body="Your saved monthly summaries will appear here."/>:<NetWorthChart points={data.net_worth.map(row=>({label:row.period_label,net_worth:row.net_worth}))}/>}
     </section>
     <section><SectionHeader title="Financial health history" description="Historical scores from saved household snapshots."/>
      {!data.health_history.length?<EmptyState title="No health history yet" body="Period scores appear after snapshots exist."/>:<div className="ipile-insights-list">{data.health_history.map(row=><div key={row.period_start}><span>{row.period_label}</span><strong>{row.score} · {row.label}</strong></div>)}</div>}
     </section>
    </TabsContent>
    <TabsContent value="spending" className="space-y-7">
     <section><SectionHeader title="Where household spending goes" description="Recorded spending ranked by category."/>
      {!data.spend.length?<EmptyState title="No spending data yet" body="Expense and giving categories will appear when activity is recorded."/>:<SpendCategoryChart points={data.spend}/>}
     </section>
     <section><SectionHeader title="Budget pressure" description="Categories reported as above their planned amount."/>
      {!data.overspend.length?<EmptyState title="No overspend signals" body="There are no categories currently reported above plan."/>:<div className="space-y-3">{data.overspend.map(row=><div key={row.category} className="ipile-insights-list-row"><div><strong>{row.category}</strong><span>Recorded amount above plan</span></div><MoneyAmount amount={row.amount} currency={currency}/><Link href="/plan/budget">Review budget</Link></div>)}</div>}
     </section>
    </TabsContent>
    <TabsContent value="giving"><section><SectionHeader title="Giving against household limits" description="Compare allocated, actual and the recorded difference to limit."/><div className="grid gap-3 md:grid-cols-3"><Metric label="Allocated" amount={data.giving.allocated} currency={currency}/><Metric label="Actual" amount={data.giving.actual} currency={currency}/><Metric label="Difference to limit" amount={data.giving.vs_limit} currency={currency}/></div></section></TabsContent>
   </Tabs>
  </ContentContainer>:null}
 </AppShell>;
}
function Metric({label,amount,currency}:{label:string;amount:string;currency:string}){return <div className="ipile-insights-metric"><p className="ipile-insights-label">{label}</p><p className="mt-3 text-xl font-medium tracking-tight"><MoneyAmount amount={amount} currency={currency}/></p></div>}
