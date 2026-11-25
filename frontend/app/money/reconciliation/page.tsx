"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/shared/AppShell";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { getAccounts, getBankConnections, getReconciliationSessions, getReconciliationSession, initiateBankConnection, syncBankConnection, disconnectBankConnection, reauthorizeBankConnection, previewReconciliationStatement, matchReconciliationItem, postReconciliationItem, ignoreReconciliationItem, completeReconciliationSession, type Account, type BankConnection, type ReconciliationCandidate, type ReconciliationSession } from "@/lib/api";

export default function ReconciliationPage() {
 const [accounts,setAccounts]=useState<Account[]|null>(null);
 const [accountId,setAccountId]=useState("");
 const [banks,setBanks]=useState<BankConnection[]>([]);
 const [sessions,setSessions]=useState<ReconciliationSession[]>([]);
 const [active,setActive]=useState<ReconciliationSession|null>(null);
 const [candidateRows,setCandidateRows]=useState<Record<string,ReconciliationCandidate[]>>({});
 const [file,setFile]=useState<File|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState<string|null>(null);
 async function refresh() {
  const [all,b,s]=await Promise.all([getAccounts(),getBankConnections(),getReconciliationSessions()]);
  const shared=all.filter(x=>x.access_scope==="shared"); setAccounts(shared); setBanks(b); setSessions(s);
  setAccountId(x=>x||shared[0]?.id||"");
  if(active) setActive(await getReconciliationSession(active.id));
 }
 useEffect(()=>{refresh().catch((e:Error)=>setError(e.message));},[]);
 async function act(fn:()=>Promise<unknown>) { setBusy(true); setError(null); try { await fn(); await refresh(); } catch(e) {setError(e instanceof Error?e.message:"Action failed.");} finally {setBusy(false);} }
 async function upload(e:FormEvent) {e.preventDefault(); if(!file||!accountId)return; await act(async()=>{setActive(await previewReconciliationStatement(accountId,file));setFile(null);});}
 if(!accounts)return <AppShell><LoadingState/></AppShell>;
 return <AppShell><ContentContainer>
  <PageHeader eyebrow="Money" title="Reconciliation & bank connections" description="Import bank activity, reconcile it against your ledger, and securely connect a bank."/>
  {error?<ErrorState message={error}/>:null}
  <div className="max-w-4xl space-y-8">
   <section className="space-y-3 border border-line p-4">
    <h2 className="font-semibold">Bank connections</h2>
    <p className="text-sm text-muted">Mono credentials must be configured by the platform administrator. Only shared accounts are eligible.</p>
    <div className="flex flex-wrap gap-2">
     <Select value={accountId} onChange={e=>setAccountId(e.target.value)}>{accounts.map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</Select>
     <Button disabled={busy||!accountId} onClick={()=>void act(async()=>{const r=await initiateBankConnection(accountId);window.location.assign(r.mono_url);})}>Connect with Mono</Button>
    </div>
    {banks.map(b=><div key={b.id} className="flex flex-wrap justify-between gap-2 border-t border-line pt-3 text-sm">
     <div><strong>{b.institution_name||"Bank"} ···· {b.masked_account_number||"----"}</strong><p className="text-xs text-muted">{b.status} / {b.data_status} {b.last_error||""}</p></div>
     <div className="flex gap-2">
      {b.status==="active"?<Button size="sm" variant="outline" disabled={busy} onClick={()=>void act(async()=>{const r=await syncBankConnection(b.id);setActive(await getReconciliationSession(r.session_id));})}>Sync</Button>:null}
      {b.status==="reauth_required"?<Button size="sm" disabled={busy} onClick={()=>void act(async()=>{const r=await reauthorizeBankConnection(b.id);window.location.assign(r.mono_url);})}>Re-authorise</Button>:null}
      {b.status!=="unlinked"?<Button size="sm" variant="outline" disabled={busy} onClick={()=>void act(()=>disconnectBankConnection(b.id))}>Disconnect</Button>:null}
     </div>
    </div>)}
   </section>
   <section className="space-y-3 border border-line p-4">
    <h2 className="font-semibold">Statement import</h2>
    <p className="text-sm text-muted">CSV and selectable-text PDF. Preview does not affect balances.</p>
    <form onSubmit={upload} className="flex flex-wrap items-end gap-3">
     <Select value={accountId} onChange={e=>setAccountId(e.target.value)}>{accounts.map(a=><option key={a.id} value={a.id}>{a.name} · {a.currency}</option>)}</Select>
     <input type="file" accept=".csv,.pdf,text/csv,application/pdf" onChange={e=>setFile(e.target.files?.[0]||null)}/>
     <Button type="submit" disabled={busy||!file||!accountId}>Preview</Button>
    </form>
   </section>
   <section className="space-y-3"><h2 className="font-semibold">Sessions</h2>
    {sessions.map(s=><button key={s.id} className="block w-full border border-line p-3 text-left text-sm" onClick={()=>void act(async()=>setActive(await getReconciliationSession(s.id)))}>
     <strong>{s.source.toUpperCase()} · {s.status}</strong><span className="block text-xs text-muted">{s.total_rows} rows · {s.matched_count} matched · {s.suggested_count} suggested · {s.unmatched_count} unmatched · {s.conflict_count} conflicts</span>
    </button>)}
   </section>
   {active?<section className="space-y-3 border border-line p-4">
    <div className="flex items-center justify-between"><h2 className="font-semibold">Review statement</h2>{active.status==="review"?<Button size="sm" variant="outline" disabled={busy} onClick={()=>void act(()=>completeReconciliationSession(active.id))}>Complete</Button>:null}</div>
    {active.balance_difference!==null?<p className="text-sm">Statement balance difference: {active.balance_difference}</p>:null}
    {(active.items||[]).map(i=><article key={i.id} className="space-y-2 border-t border-line py-3 text-sm">
     <div className="flex justify-between gap-2"><strong>{i.merchant||i.description||"Transaction"}</strong><strong>{i.currency} {i.amount}</strong></div>
     <p className="text-xs text-muted">{i.date} · {i.type} · {i.status} · {i.match_reason||""}</p>
     {i.suggested_transaction?<p className="text-xs">Suggested: {i.suggested_transaction.date} / {i.suggested_transaction.merchant||i.suggested_transaction.description}</p>:null}
     {active.status==="review"&&!["matched","posted","ignored"].includes(i.status)?<div className="flex flex-wrap gap-2">
      {i.suggested_transaction?<Button size="sm" disabled={busy} onClick={()=>void act(()=>matchReconciliationItem(i.id,i.suggested_transaction!.id))}>Confirm suggested match</Button>:null}
      <Button size="sm" variant="outline" disabled={busy} onClick={()=>void act(async()=>setCandidateRows(current=>({...current,[i.id]:await getReconciliationCandidates(i.id)})))}>Find ledger matches</Button>
      {(candidateRows[i.id]||[]).map(tx=><Button key={tx.id} size="sm" variant="outline" disabled={busy} onClick={()=>void act(()=>matchReconciliationItem(i.id,tx.id))}>Match {tx.date} · {tx.merchant||tx.description||tx.amount}</Button>)}
      {i.type!=="transfer"?<Button size="sm" variant="outline" disabled={busy} onClick={()=>void act(()=>postReconciliationItem(i.id))}>Post new transaction</Button>:null}
      <Button size="sm" variant="ghost" disabled={busy} onClick={()=>void act(()=>ignoreReconciliationItem(i.id))}>Ignore</Button>
     </div>:null}
    </article>)}
   </section>:null}
  </div>
 </ContentContainer></AppShell>;
}
