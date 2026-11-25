"use client";
import { useEffect, useMemo, useState } from "react";
import { Download, FileText } from "lucide-react";
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
import { useHouseholdCurrency } from "@/hooks/useHouseholdCurrency";
import { getAnnualReport,getGivingReport,getMonthlyReport,getQuarterlyReport,type Report } from "@/lib/api";

const kinds=["monthly","quarterly","annual","giving"] as const;
type Kind=(typeof kinds)[number];
const now=new Date();
const currentMonth=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
const currentYear=now.getFullYear();
const currentQuarter=Math.floor(now.getMonth()/3)+1;
const moneyKeys=["income","expenses","savings","investments","giving","debt_reduction","surplus","net_worth_change","allocated","actual","limit","vs_limit"];

export default function ReportsPage(){
 const [kind,setKind]=useState<Kind>("monthly");
 const [month,setMonth]=useState(currentMonth);
 const [year,setYear]=useState(currentYear);
 const [quarter,setQuarter]=useState(currentQuarter);
 const [report,setReport]=useState<Report|null>(null);
 const [error,setError]=useState<string|null>(null);
 const [pending,setPending]=useState(true);
 const currency=useHouseholdCurrency();

 useEffect(()=>{
  let active=true;
  setPending(true);setError(null);setReport(null);
  const load=kind==="monthly"?getMonthlyReport(`${month}-01`):kind==="quarterly"?getQuarterlyReport(year,quarter):kind==="annual"?getAnnualReport(year):getGivingReport(year);
  load.then(value=>{if(active)setReport(value)}).catch((err:Error)=>{if(active)setError(err.message)}).finally(()=>{if(active)setPending(false)});
  return()=>{active=false};
 },[kind,month,quarter,year]);

 const periodLabel=useMemo(()=>kind==="monthly"?new Date(`${month}-01T12:00:00`).toLocaleDateString(undefined,{month:"long",year:"numeric"}):kind==="quarterly"?`Q${quarter} ${year}`:String(year),[kind,month,quarter,year]);

 function downloadReport(){
  if(!report)return;
  const rows=[["Field","Value"],...Object.entries(report.payload).map(([key,value])=>[key,typeof value==="object"?JSON.stringify(value):String(value??"")])];
  const csv=rows.map(row=>row.map(value=>`"${value.replaceAll('"','""')}"`).join(",")).join("\n");
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const anchor=document.createElement("a");anchor.href=url;anchor.download=`ipile-${kind}-report-${report.period_start}.csv`;anchor.click();URL.revokeObjectURL(url);
 }

 return <AppShell><ContentContainer className="ipile-reports-workspace">
  <PageHeader eyebrow="Household intelligence" title="Reports" description="A clear, period-based record of your household's financial activity." actions={<Button type="button" variant="outline" disabled={!report||pending} onClick={downloadReport}><Download className="mr-2 h-4 w-4"/>Export CSV</Button>}/>
  <section className="ipile-report-intro"><div><p className="ipile-insights-label">Financial reporting</p><h2>Make the numbers easier to understand.</h2><p>Choose a reporting period to review recorded figures and export the report for your records.</p></div><div className="ipile-report-intro-icon"><FileText aria-hidden/></div></section>
  <Tabs value={kind} onValueChange={value=>setKind(value as Kind)}>
   <TabsList>{kinds.map(row=><TabsTrigger key={row} value={row} className="capitalize">{row}</TabsTrigger>)}</TabsList>
   <div className="ipile-report-controls">
    {kind==="monthly"?<label>Month<input aria-label="Report month" type="month" value={month} max={currentMonth} onChange={e=>setMonth(e.target.value)}/></label>:null}
    {kind==="quarterly"?<label>Quarter<select aria-label="Report quarter" value={quarter} onChange={e=>setQuarter(Number(e.target.value))}>{[1,2,3,4].map(q=><option key={q} value={q}>Q{q}</option>)}</select></label>:null}
    {kind!=="monthly"?<label>Year<input aria-label="Report year" type="number" min="2000" max={currentYear} value={year} onChange={e=>setYear(Math.min(currentYear,Math.max(2000,Number(e.target.value)||currentYear)))}/></label>:null}
    <div className="ipile-report-period"><span>Selected period</span><strong>{periodLabel}</strong></div>
   </div>
   {kinds.map(row=><TabsContent key={row} value={row}>
    {pending?<LoadingState/>:null}
    {error?<><ErrorState message={error}/><Button type="button" variant="outline" onClick={()=>{setError(null);setPending(true);const load=kind==="monthly"?getMonthlyReport(`${month}-01`):kind==="quarterly"?getQuarterlyReport(year,quarter):kind==="annual"?getAnnualReport(year):getGivingReport(year);load.then(setReport).catch((err:Error)=>setError(err.message)).finally(()=>setPending(false))}}>Try again</Button></>:null}
    {report&&!pending&&kind===row?<ReportBody report={report} currency={currency??"NGN"}/>:null}
   </TabsContent>)}
  </Tabs>
 </ContentContainer></AppShell>;
}

function ReportBody({report,currency}:{report:Report;currency:string}){
 const payload=report.payload;
 const figures=moneyKeys.filter(key=>typeof payload[key]==="string");
 return <article className="ipile-report-card">
  <div className="ipile-report-card-heading"><div><p className="ipile-insights-label">{String(payload.title??report.kind)}</p><h2>{String(payload.period_label??report.period_start)}</h2><p>{report.period_start} — {report.period_end}</p></div><span>Household report</span></div>
  {figures.length?<section><SectionHeader title="Financial summary" description="Figures returned by the household reporting service."/><div className="ipile-report-figures">{figures.map(key=><div key={key}><span>{key.replaceAll("_"," ")}</span><strong><MoneyAmount amount={payload[key] as string} currency={currency}/></strong></div>)}</div></section>:<EmptyState title="No financial figures in this report" body="The selected report does not contain summary figures yet."/>}
  {typeof payload.health_score==="string"?<section className="ipile-report-note"><span>Financial health</span><strong>{payload.health_score}/100{typeof payload.health_label==="string"?` · ${payload.health_label}`:""}</strong></section>:null}
  {payload.top_overspend&&typeof payload.top_overspend==="object"?<section className="ipile-report-note"><span>Top overspend</span><strong>{(payload.top_overspend as {category:string}).category} · <MoneyAmount amount={(payload.top_overspend as {amount:string}).amount} currency={currency}/></strong></section>:null}
  {typeof payload.best_improvement==="string"?<section className="ipile-report-note"><span>Best improvement</span><strong>{payload.best_improvement}</strong></section>:null}
  {payload.upcoming_risk&&typeof payload.upcoming_risk==="object"?<section className="ipile-report-note"><span>Upcoming risk</span><strong>{(payload.upcoming_risk as {title:string}).title} · {(payload.upcoming_risk as {date:string}).date}</strong></section>:null}
 </article>;
}
