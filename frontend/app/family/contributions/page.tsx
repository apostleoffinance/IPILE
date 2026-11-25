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
  getContributionForecast,
  listContributionAgreements,
  listContributionRecords,
  listContributionSchedule,
  updateContributionAgreement,
  recordContribution,
  type ContributionAgreement,
  type ContributionRecord,
  type Member,
  type ContributionScheduleRow,
  type ContributionForecast,
  api,
} from "@/lib/api";

export default function ContributionsPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [currentMember, setCurrentMember] = useState<Member | null>(null);
  const [schedule, setSchedule] = useState<ContributionScheduleRow[]>([]);
  const [forecast, setForecast] = useState<ContributionForecast | null>(null);
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
  const [editingAgreementId, setEditingAgreementId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editCadence, setEditCadence] = useState("monthly");
  const [editDueDay, setEditDueDay] = useState("1");
  const [editEndDate, setEditEndDate] = useState("");
  const [editStatus, setEditStatus] = useState("active");
  const [editNotes, setEditNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [memberRows, me, agreementRows, scheduleRows, forecastRows] = await Promise.all([
      api.members(),
      api.currentMember(),
      listContributionAgreements(),
      listContributionSchedule(),
      getContributionForecast(),
    ]);
    setMembers(memberRows);
    setCurrentMember(me);
    setSchedule(scheduleRows);
    setForecast(forecastRows);
    setAgreements(agreementRows);
    if (!memberId && memberRows[0]) setMemberId(memberRows[0].id);
    const entries = await Promise.all(
      agreementRows.map(async (row) => [row.id, await listContributionRecords(row.id)] as const),
    );
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

  function startEditAgreement(agreement: ContributionAgreement) {
    setEditingAgreementId(agreement.id);
    setEditAmount(agreement.amount);
    setEditCadence(agreement.cadence);
    setEditDueDay(String(agreement.due_day ?? 1));
    setEditEndDate(agreement.end_date ?? "");
    setEditStatus(agreement.status);
    setEditNotes(agreement.notes ?? "");
  }

  async function onUpdateAgreement(event: FormEvent) {
    event.preventDefault();
    if (!editingAgreementId || !editAmount) return;
    setBusy(true);
    setError(null);
    try {
      await updateContributionAgreement(editingAgreementId, {
        amount: editAmount,
        cadence: editCadence,
        due_day: editCadence === "monthly" ? Number(editDueDay) : null,
        end_date: editEndDate || null,
        status: editStatus,
        notes: editNotes || null,
      });
      setEditingAgreementId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update agreement.");
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
        <div className="ipile-family-page ipile-family-contributions">
        <PageHeader
          eyebrow="Household governance"
          title="Contribution agreements"
          description="Set expected household contributions, track what has been received, and keep an auditable record."
        />
        {error ? <ErrorState message={error} /> : null}
        {currentMember && ["owner", "partner"].includes(currentMember.role) ? (
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
        ) : null}

        <section className="mb-8 space-y-3">
          <h2 className="font-semibold">Contribution schedule</h2>
          {schedule.length === 0 ? (
            <p className="border border-line p-4 text-sm text-muted">No scheduled contributions in this period.</p>
          ) : (
            <div className="overflow-x-auto border border-line bg-surface">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-3">Due date</th>
                    <th className="px-4 py-3">Agreement</th>
                    <th className="px-4 py-3 text-right">Expected</th>
                    <th className="px-4 py-3 text-right">Recorded</th>
                    <th className="px-4 py-3 text-right">Outstanding</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {schedule.map((row) => (
                    <tr key={`${row.agreement_id}-${row.due_date}`} className="border-b border-line last:border-0">
                      <td className="px-4 py-3">{row.due_date}</td>
                      <td className="px-4 py-3">{row.name}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{row.currency} {row.expected_amount}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{row.currency} {row.paid_amount}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{row.currency} {row.outstanding_amount}</td>
                      <td className="px-4 py-3 capitalize">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-xs text-muted">
            Recorded amounts include reported payments. Only matching cleared or reconciled income in shared household accounts counts as verified receipts in financial forecasts.
          </p>
        </section>

        {forecast ? (
          <section className="mb-8 space-y-3">
            <div>
              <h2 className="font-semibold">Contribution forecast · {forecast.horizon_days} days</h2>
              <p className="text-sm text-muted">Expected commitments are forecasts, not cash on hand. Verified receipts are already recorded in the shared ledger.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              {[
                ["Expected", forecast.expected],
                ["Verified received", forecast.verified_received],
                ["Outstanding", forecast.outstanding],
              ].map(([label, value]) => (
                <div key={label} className="border border-line bg-surface p-4">
                  <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
                  <p className="mt-2 text-xl font-semibold tabular-nums">{forecast.currency} {value}</p>
                </div>
              ))}
            </div>
            {Object.keys(forecast.other_currency_outstanding).length > 0 ? (
              <p className="text-xs text-muted">
                Other currencies are shown separately and are not converted without an exchange rate: {Object.entries(forecast.other_currency_outstanding).map(([code, value]) => `${code} ${value}`).join(" · ")}
              </p>
            ) : null}
          </section>
        ) : null}

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
              {currentMember && ["owner", "partner"].includes(currentMember.role) ? (
                <div className="flex justify-end">
                  <Button type="button" variant="outline" size="sm" onClick={() => startEditAgreement(agreement)}>
                    Edit agreement
                  </Button>
                </div>
              ) : null}
              {editingAgreementId === agreement.id ? (
                <form onSubmit={onUpdateAgreement} className="grid gap-3 border-t border-line pt-3 md:grid-cols-2">
                  <div>
                    <Label htmlFor={`edit-contribution-amount-${agreement.id}`}>Expected amount</Label>
                    <Input id={`edit-contribution-amount-${agreement.id}`} className="mt-1" type="number" min="0.01" step="0.01" value={editAmount} onChange={(event) => setEditAmount(event.target.value)} required />
                  </div>
                  <div>
                    <Label htmlFor={`edit-contribution-cadence-${agreement.id}`}>Frequency</Label>
                    <Select id={`edit-contribution-cadence-${agreement.id}`} className="mt-1" value={editCadence} onChange={(event) => setEditCadence(event.target.value)}>
                      <option value="weekly">Weekly</option><option value="biweekly">Every two weeks</option>
                      <option value="monthly">Monthly</option><option value="quarterly">Quarterly</option>
                      <option value="annually">Annually</option><option value="one_off">One-off</option>
                    </Select>
                  </div>
                  {editCadence === "monthly" ? (
                    <div>
                      <Label htmlFor={`edit-contribution-due-${agreement.id}`}>Due day</Label>
                      <Input id={`edit-contribution-due-${agreement.id}`} className="mt-1" type="number" min="1" max="31" value={editDueDay} onChange={(event) => setEditDueDay(event.target.value)} required />
                    </div>
                  ) : null}
                  <div>
                    <Label htmlFor={`edit-contribution-end-${agreement.id}`}>End date (optional)</Label>
                    <Input id={`edit-contribution-end-${agreement.id}`} className="mt-1" type="date" value={editEndDate} onChange={(event) => setEditEndDate(event.target.value)} />
                  </div>
                  <div>
                    <Label htmlFor={`edit-contribution-status-${agreement.id}`}>Status</Label>
                    <Select id={`edit-contribution-status-${agreement.id}`} className="mt-1" value={editStatus} onChange={(event) => setEditStatus(event.target.value)}>
                      <option value="active">Active</option><option value="paused">Paused</option>
                      <option value="completed">Completed</option><option value="cancelled">Cancelled</option>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor={`edit-contribution-notes-${agreement.id}`}>Notes</Label>
                    <Input id={`edit-contribution-notes-${agreement.id}`} className="mt-1" value={editNotes} onChange={(event) => setEditNotes(event.target.value)} />
                  </div>
                  <div className="flex items-end gap-2 md:col-span-2">
                    <Button type="submit" disabled={busy}>Save agreement</Button>
                    <Button type="button" variant="ghost" onClick={() => setEditingAgreementId(null)}>Cancel</Button>
                  </div>
                </form>
              ) : null}
              {currentMember && (
                ["owner", "partner"].includes(currentMember.role) ||
                (currentMember.role === "member" && agreement.member_id === currentMember.id)
              ) ? (
              <form onSubmit={(event) => void onRecord(event, agreement.id)} className="grid gap-3 border-t border-line pt-3 md:grid-cols-3">
                <div><Label htmlFor={`record-amount-${agreement.id}`}>Amount received</Label><Input id={`record-amount-${agreement.id}`} className="mt-1" type="number" min="0.01" step="0.01" value={recordAmounts[agreement.id] ?? ""} onChange={(e) => setRecordAmounts((current) => ({ ...current, [agreement.id]: e.target.value }))} required /></div>
                <div><Label htmlFor={`record-date-${agreement.id}`}>Received on</Label><Input id={`record-date-${agreement.id}`} className="mt-1" type="date" value={recordDates[agreement.id] ?? ""} onChange={(e) => setRecordDates((current) => ({ ...current, [agreement.id]: e.target.value }))} required /></div>
                <div className="flex items-end"><Button type="submit" disabled={busy}>{busy ? "Saving..." : "Record contribution"}</Button></div>
              </form>
              ) : null}
              <div className="space-y-2">
                <h3 className="text-sm font-medium">Contribution history</h3>
                {history.length === 0 ? <p className="text-sm text-muted">No contributions recorded.</p> : history.map((row) => <div key={row.id} className="flex justify-between gap-3 border-t border-line pt-2 text-sm"><span>{row.contributed_on}{row.note ? ` · ${row.note}` : ""}</span><span className="font-medium tabular-nums">{row.currency} {row.amount}</span></div>)}
              </div>
            </section>;
          })}
        </div>
              </div>
      </ContentContainer>
    </AppShell>
  );
}
