"use client";

import { FormEvent, useEffect, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  createContributionAgreement,
  listContributionAgreements,
  listContributionRecords,
  recordContribution,
  type ContributionAgreement,
  type ContributionRecord,
  type Member,
  api,
} from "@/lib/api";

export default function ContributionsPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [agreements, setAgreements] = useState<ContributionAgreement[]>([]);
  const [records, setRecords] = useState<Record<string, ContributionRecord[]>>({});
  const [memberId, setMemberId] = useState("");
  const [name, setName] = useState("Household contribution");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("NGN");
  const [cadence, setCadence] = useState("monthly");
  const [dueDay, setDueDay] = useState("1");
  const [startDate, setStartDate] = useState("");
  const [recordAmounts, setRecordAmounts] = useState<Record<string, string>>({});
  const [recordDates, setRecordDates] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [memberRows, agreementRows] = await Promise.all([api.members(), listContributionAgreements()]);
    setMembers(memberRows);
    setAgreements(agreementRows);
    if (!memberId && memberRows[0]) setMemberId(memberRows[0].id);
    const entries = await Promise.all(agreementRows.map(async (row) => [row.id, await listContributionRecords(row.id)] as const));
    setRecords(Object.fromEntries(entries));
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message)).finally(() => setLoaded(true));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!memberId || !startDate || !amount) return;
    setBusy(true);
    setError(null);
    try {
      await createContributionAgreement({
        member_id: memberId, name, amount, currency, cadence,
        ...(cadence === "monthly" ? { due_day: Number(dueDay) } : {}),
        start_date: startDate,
      });
      setAmount("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create agreement.");
    } finally {
      setBusy(false);
    }
  }

  async function onRecord(event: FormEvent, agreementId: string) {
    event.preventDefault();
    const value = recordAmounts[agreementId];
    const date = recordDates[agreementId];
    if (!value || !date) return;
    setBusy(true);
    setError(null);
    try {
      await recordContribution(agreementId, { amount: value, contributed_on: date });
      setRecordAmounts((current) => ({ ...current, [agreementId]: "" }));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record contribution.");
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return <AppShell><LoadingState /></AppShell>;

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Household governance"
          title="Contribution agreements"
          description="Set expected household contributions, track what has been received, and keep an auditable record."
        />
        {error ? <ErrorState message={error} /> : null}
        <form onSubmit={onCreate} className="mb-8 grid gap-4 border border-line bg-surface p-5 md:grid-cols-2">
          <div className="md:col-span-2"><h2 className="font-semibold">Create an agreement</h2></div>
          <div>
            <Label htmlFor="contributor">Contributor</Label>
            <Select id="contributor" className="mt-1" value={memberId} onChange={(e) => setMemberId(e.target.value)} required>
              {members.map((member) => <option key={member.id} value={member.id}>{member.display_name}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="agreement-name">Agreement name</Label>
            <Input id="agreement-name" className="mt-1" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="agreement-amount">Expected amount</Label>
            <Input id="agreement-amount" className="mt-1" type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="agreement-currency">Currency</Label>
            <Input id="agreement-currency" className="mt-1" minLength={3} maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} required />
          </div>
          <div>
            <Label htmlFor="agreement-cadence">Frequency</Label>
            <Select id="agreement-cadence" className="mt-1" value={cadence} onChange={(e) => setCadence(e.target.value)}>
              <option value="weekly">Weekly</option><option value="biweekly">Every two weeks</option>
              <option value="monthly">Monthly</option><option value="quarterly">Quarterly</option>
              <option value="annually">Annually</option><option value="one_off">One-off</option>
            </Select>
          </div>
          {cadence === "monthly" ? <div>
            <Label htmlFor="agreement-due-day">Due day of month</Label>
            <Input id="agreement-due-day" className="mt-1" type="number" min="1" max="31" value={dueDay} onChange={(e) => setDueDay(e.target.value)} required />
          </div> : null}
          <div>
            <Label htmlFor="agreement-start">Start date</Label>
            <Input id="agreement-start" className="mt-1" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
          </div>
          <div className="md:col-span-2"><Button type="submit" disabled={busy || members.length === 0}>{busy ? "Saving..." : "Create agreement"}</Button></div>
        </form>

        <div className="space-y-5">
          {agreements.length === 0 ? <p className="border border-line p-5 text-sm text-muted">No contribution agreements yet.</p> : agreements.map((agreement) => {
            const member = members.find((row) => row.id === agreement.member_id);
            const history = records[agreement.id] ?? [];
            return <section key={agreement.id} className="space-y-3 border border-line bg-surface p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><h2 className="font-semibold">{agreement.name}</h2><p className="text-sm text-muted">{member?.display_name ?? "Household member"} · {agreement.cadence.replace("_", " ")} · Due {agreement.due_day ?? "—"}</p></div>
                <p className="font-semibold tabular-nums">{agreement.currency} {agreement.amount}</p>
              </div>
              <p className="text-xs text-muted">Status: {agreement.status} · Starts {agreement.start_date}{agreement.end_date ? ` · Ends ${agreement.end_date}` : ""}</p>
              <form onSubmit={(event) => void onRecord(event, agreement.id)} className="grid gap-3 border-t border-line pt-3 md:grid-cols-3">
                <div><Label htmlFor={`record-amount-${agreement.id}`}>Amount received</Label><Input id={`record-amount-${agreement.id}`} className="mt-1" type="number" min="0.01" step="0.01" value={recordAmounts[agreement.id] ?? ""} onChange={(e) => setRecordAmounts((current) => ({ ...current, [agreement.id]: e.target.value }))} required /></div>
                <div><Label htmlFor={`record-date-${agreement.id}`}>Received on</Label><Input id={`record-date-${agreement.id}`} className="mt-1" type="date" value={recordDates[agreement.id] ?? ""} onChange={(e) => setRecordDates((current) => ({ ...current, [agreement.id]: e.target.value }))} required /></div>
                <div className="flex items-end"><Button type="submit" disabled={busy}>{busy ? "Saving..." : "Record contribution"}</Button></div>
              </form>
              <div className="space-y-2">
                <h3 className="text-sm font-medium">Contribution history</h3>
                {history.length === 0 ? <p className="text-sm text-muted">No contributions recorded.</p> : history.map((row) => <div key={row.id} className="flex justify-between gap-3 border-t border-line pt-2 text-sm"><span>{row.contributed_on}{row.note ? ` · ${row.note}` : ""}</span><span className="font-medium tabular-nums">{row.currency} {row.amount}</span></div>)}
              </div>
            </section>;
          })}
        </div>
      </ContentContainer>
    </AppShell>
  );
}
