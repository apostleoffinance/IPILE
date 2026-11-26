"use client";

import { FormEvent, useEffect, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  approveEmailImport,
  connectGmail,
  disconnectGmail,
  getGmailConnection,
  getImportPreferences,
  syncGmail,
  updateImportPreferences,
  commitStagedImport,
  createImportMailbox,
  correctEmailImport,
  getAccounts,
  getImportReview,
  previewImport,
  previewStatementUpload,
  type Account,
  type ImportJob,
  type GmailConnectionStatus,
  type ImportAutomationMode,
} from "@/lib/api";

const CSV_HINT = "Use a bank-exported CSV with a transaction date and amount. Debit and credit columns are supported. A description or merchant name is helpful but optional.";
const STATEMENT_HINT = "For pasted statements, put the date, amount, description and optional reference on each line, separated by |. Negative amounts mean money received; positive amounts mean money spent.";

export default function ImportPage() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accountId, setAccountId] = useState("");
  const [source, setSource] = useState<"csv" | "statement">("csv");
  const [content, setContent] = useState("");
  const [filename, setFilename] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportJob | null>(null);
  const [mailboxAddress, setMailboxAddress] = useState<string | null>(null);
  const [emailJobs, setEmailJobs] = useState<ImportJob[]>([]);
  const [reviewAccounts, setReviewAccounts] = useState<Record<string, string>>({});
  const [emailCorrections, setEmailCorrections] = useState<Record<string, { amount?: string; date?: string; type?: "income" | "expense"; description?: string }>>({});
  const [mailboxBusy, setMailboxBusy] = useState(false);
  const [gmail, setGmail] = useState<GmailConnectionStatus | null>(null);
  const [gmailBusy, setGmailBusy] = useState(false);
  const [automationMode, setAutomationMode] = useState<ImportAutomationMode>("review_everything");

  async function refreshEmailReview() {
    const jobs = await getImportReview();
    const pendingEmailJobs = jobs.filter((job) => job.source === "email");
    setEmailJobs(pendingEmailJobs);
    setReviewAccounts((current) => {
      const next = { ...current };
      for (const job of pendingEmailJobs) {
        if (!next[job.id] && accounts?.length) next[job.id] = accounts.find((account) => account.id === job.result?.suggested_account_id)?.id ?? accounts[0].id;
      }
      return next;
    });
  }

  useEffect(() => {
    getAccounts()
      .then(async (rows) => {
        setAccounts(rows);
        if (rows[0]) setAccountId(rows[0].id);
        try {
          const jobs = await getImportReview();
          setEmailJobs(jobs.filter((job) => job.source === "email"));
        } catch {
          // Keep statement imports usable if the review queue is temporarily unavailable.
        }
        try {
          const [connection, preferences] = await Promise.all([
            getGmailConnection(),
            getImportPreferences(),
          ]);
          setGmail(connection);
          setAutomationMode(preferences.automation_mode);
        } catch {
          // Email forwarding remains available if Gmail integration is not configured.
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!accountId || (!file && !content.trim())) return;
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const job = file
        ? await previewStatementUpload(accountId, file)
        : await previewImport({ account_id: accountId, source, content, filename: filename || undefined });
      setResult(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not prepare this import.");
    } finally {
      setPending(false);
    }
  }

  async function onCommit(jobId: string) {
    if (!accountId) return;
    setPending(true);
    setError(null);
    try {
      setResult(await commitStagedImport(jobId, accountId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm this import.");
    } finally {
      setPending(false);
    }
  }

  async function onCreateMailbox() {
    setMailboxBusy(true);
    setError(null);
    try {
      const mailbox = await createImportMailbox();
      setMailboxAddress(mailbox.address);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create an inbound email address.");
    } finally {
      setMailboxBusy(false);
    }
  }

  async function onConnectGmail() {
    setGmailBusy(true);
    setError(null);
    try {
      const result = await connectGmail();
      window.location.assign(result.authorization_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Gmail connection.");
      setGmailBusy(false);
    }
  }

  async function onSyncGmail() {
    setGmailBusy(true);
    setError(null);
    try {
      await syncGmail();
      await refreshEmailReview();
      setGmail(await getGmailConnection());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sync Gmail.");
    } finally {
      setGmailBusy(false);
    }
  }

  async function onDisconnectGmail() {
    setGmailBusy(true);
    setError(null);
    try {
      await disconnectGmail();
      setGmail(await getGmailConnection());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not disconnect Gmail.");
    } finally {
      setGmailBusy(false);
    }
  }

  async function onAutomationChange(value: ImportAutomationMode) {
    setAutomationMode(value);
    setError(null);
    try {
      const saved = await updateImportPreferences(value);
      setAutomationMode(saved.automation_mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update automation preferences.");
      setAutomationMode("review_everything");
    }
  }

  async function onCorrectEmail(job: ImportJob) {
    const row = job.result?.rows?.[0];
    if (!row) return;
    const correction = emailCorrections[job.id] ?? {};
    setPending(true);
    setError(null);
    try {
      await correctEmailImport(job.id, {
        amount: correction.amount ?? String(row.amount),
        date: correction.date ?? String(row.date),
        type: correction.type ?? (row.type as "income" | "expense"),
        description: correction.description ?? String(row.description ?? ""),
      });
      await refreshEmailReview();
      setEmailCorrections((current) => {
        const next = { ...current };
        delete next[job.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save these corrections.");
    } finally {
      setPending(false);
    }
  }

  async function onApproveEmail(job: ImportJob) {
    const destination = reviewAccounts[job.id];
    if (!destination) return;
    setPending(true);
    setError(null);
    try {
      await approveEmailImport(job.id, destination);
      await refreshEmailReview();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve this bank alert.");
    } finally {
      setPending(false);
    }
  }

  if (!accounts) return <AppShell><LoadingState /></AppShell>;

  return (
    <AppShell>
      <ContentContainer className="ipile-workspace ipile-money-workspace">
        <PageHeader
          eyebrow="Money"
          title="Import transactions"
          description="Import a bank statement or forward bank alerts by email. Review every item before it enters your household ledger."
        />
        {error ? <ErrorState message={error} /> : null}
        <div className="max-w-3xl space-y-8">
          <section className="space-y-4 border border-line p-4">
            <h2 className="font-semibold">1. Connect your bank-alert inbox</h2>
            <p className="text-sm text-muted">
              Connect Gmail once for automatic read-only monitoring, or use the private forwarding address as an alternative for other email providers.
            </p>
            <div className="space-y-2 border border-line bg-surface p-3">
              {gmail?.connected ? (
                <>
                  <p className="text-sm font-medium">Gmail connected · {gmail.email_address}</p>
                  <p className="text-xs text-muted">Read-only access. IPÌLẸ̀ searches for supported bank alerts; it cannot send, modify or delete your emails.</p>
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="outline" disabled={gmailBusy} onClick={() => void onSyncGmail()}>{gmailBusy ? "Syncing..." : "Sync now"}</Button>
                    <Button type="button" size="sm" variant="ghost" disabled={gmailBusy} onClick={() => void onDisconnectGmail()}>Disconnect Gmail</Button>
                  </div>
                  {gmail.last_sync_at ? <p className="text-xs text-muted">Last checked: {new Date(gmail.last_sync_at).toLocaleString()}</p> : null}
                  {gmail.last_error ? <p className="text-xs text-danger">{gmail.last_error}</p> : null}
                </>
              ) : (
                <>
                  <p className="text-sm font-medium">Gmail · Recommended</p>
                  <p className="text-xs text-muted">Connect the inbox where your bank alerts already arrive. You approve access through Google.</p>
                  <Button type="button" disabled={gmailBusy} onClick={() => void onConnectGmail()}>{gmailBusy ? "Connecting..." : "Connect Gmail"}</Button>
                </>
              )}
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Other email providers</p>
              <p className="text-xs text-muted">Create the private IPÌLẸ̀ address below, then add a one-time forwarding/filter rule in your email provider. Only bank-alert emails should be forwarded; you do not need to forward each alert manually.</p>
            </div>
            {mailboxAddress ? (
              <div className="space-y-2 border border-line bg-surface p-3">
                <p className="break-all font-mono text-sm">{mailboxAddress}</p>
                <Button type="button" variant="outline" onClick={() => void navigator.clipboard.writeText(mailboxAddress)}>
                  Copy email address
                </Button>
                <p className="text-xs text-muted">
                  Keep this address private. Generating another address invalidates this one. If you leave this page, generate a new address to retrieve one.
                </p>
              </div>
            ) : null}
            <Button type="button" variant="outline" disabled={mailboxBusy} onClick={() => void onCreateMailbox()}>
              {mailboxBusy ? "Generating..." : mailboxAddress ? "Generate a new address" : "Generate bank-alert email"}
            </Button>
            <p className="text-xs text-muted">
              Only verified bank sender domains are accepted. Alerts with unclear amounts or dates are held for review as rejected items. Email attachments are not imported automatically.
            </p>
          </section>

          <section className="space-y-3 border border-line p-4">
            <h2 className="font-semibold">2. Automation preferences</h2>
            <p className="text-sm text-muted">Choose how much control IPÌLẸ̀ should take. You can change this at any time.</p>
            <label className="block text-sm">
              <span className="text-muted">Transaction handling</span>
              <Select className="mt-1" value={automationMode} onChange={(event) => void onAutomationChange(event.target.value as ImportAutomationMode)}>
                <option value="review_everything">Review every transaction (recommended)</option>
                <option value="auto_trusted">Automatically record trusted, matched alerts</option>
                <option value="full_automation">Full automation for confidently matched alerts</option>
              </Select>
            </label>
            <p className="text-xs text-muted">Even with automation enabled, IPÌLẸ̀ will hold uncertain amounts, currencies, senders and account matches for review. It will never guess a destination account.</p>
          </section>

          <section className="space-y-4 border border-line p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">3. Review incoming bank alerts</h2>
              <Button type="button" size="sm" variant="outline" onClick={() => void refreshEmailReview()}>Refresh</Button>
            </div>
            {emailJobs.length === 0 ? (
              <EmptyState title="No email alerts to review" body="Forward a bank transaction alert to your private IPÌLẸ̀ address. New alerts will appear here." />
            ) : emailJobs.map((job) => {
              const row = job.result?.rows?.[0];
              const rejected = job.status === "rejected";
              return (
                <article key={job.id} className="space-y-3 border border-line p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">{job.filename || "Bank alert"}</p>
                    <span className="text-xs uppercase text-muted">{job.status.replaceAll("_", " ")}</span>
                  </div>
                  <p className="text-xs text-muted">From: {String(job.result?.sender ?? "Unknown sender")}</p>
                  {row ? (
                    <div className="grid gap-1 text-sm sm:grid-cols-2">
                      <p>{row.date} · {row.type} · {row.currency ?? "Currency not detected"}</p>
                      <p className="font-semibold">{row.amount}</p>
                      <p className="text-muted sm:col-span-2">{row.description || row.merchant || "Bank transaction"}</p>
                      {row.external_id ? <p className="text-xs text-muted sm:col-span-2">Reference: {row.external_id}</p> : null}
                    </div>
                  ) : null}
                  {rejected ? (
                    <ul className="list-disc pl-5 text-sm text-muted">
                      {(job.result?.errors ?? ["This alert could not be parsed safely."]).map((message) => <li key={message}>{message}</li>)}
                    </ul>
                  ) : (
                    <div className="space-y-2">
                      <div className="grid gap-2 sm:grid-cols-2">
                        <label className="block text-sm">
                          <span className="text-muted">Amount</span>
                          <Input className="mt-1" inputMode="decimal" value={emailCorrections[job.id]?.amount ?? String(row?.amount ?? "")} onChange={(event) => setEmailCorrections((current) => ({ ...current, [job.id]: { ...current[job.id], amount: event.target.value } }))} />
                        </label>
                        <label className="block text-sm">
                          <span className="text-muted">Transaction date</span>
                          <Input className="mt-1" type="date" value={emailCorrections[job.id]?.date ?? String(row?.date ?? "")} onChange={(event) => setEmailCorrections((current) => ({ ...current, [job.id]: { ...current[job.id], date: event.target.value } }))} />
                        </label>
                        <label className="block text-sm">
                          <span className="text-muted">Direction</span>
                          <Select className="mt-1" value={emailCorrections[job.id]?.type ?? row?.type ?? "expense"} onChange={(event) => setEmailCorrections((current) => ({ ...current, [job.id]: { ...current[job.id], type: event.target.value as "income" | "expense" } }))}>
                            <option value="income">Money in</option>
                            <option value="expense">Money out</option>
                          </Select>
                        </label>
                        <label className="block text-sm">
                          <span className="text-muted">Description</span>
                          <Input className="mt-1" value={emailCorrections[job.id]?.description ?? String(row?.description ?? "")} onChange={(event) => setEmailCorrections((current) => ({ ...current, [job.id]: { ...current[job.id], description: event.target.value } }))} />
                        </label>
                      </div>
                      <Button type="button" variant="outline" disabled={pending} onClick={() => void onCorrectEmail(job)}>
                        Save corrections
                      </Button>
                      <label className="block text-sm">
                        <span className="text-muted">Post to account</span>
                        <Select className="mt-1" value={reviewAccounts[job.id] ?? (accounts.some((account) => account.id === job.result?.suggested_account_id) ? String(job.result?.suggested_account_id) : accounts[0]?.id) ?? ""} onChange={(event) => setReviewAccounts((current) => ({ ...current, [job.id]: event.target.value }))}>
                          {accounts.map((account) => <option key={account.id} value={account.id}>{account.name} · {account.currency}</option>)}
                        </Select>
                      </label>
                      <Button type="button" disabled={pending || accounts.length === 0} onClick={() => void onApproveEmail(job)}>
                        {pending ? "Processing..." : "Approve and add transaction"}
                      </Button>
                    </div>
                  )}
                </article>
              );
            })}
            <p className="text-xs text-muted">Approval is required before an alert changes your transaction history or account balance.</p>
          </section>

          <section className="space-y-4 border border-line p-4">
            <h2 className="font-semibold">4. Import a bank statement</h2>
            {accounts.length === 0 ? (
              <EmptyState title="Add an account first" body="Imports are reviewed and posted against a household bank or cash account." />
            ) : (
              <>
                <form className="space-y-4" onSubmit={onSubmit}>
                  <label className="block text-sm">
                    <span className="text-muted">Destination account</span>
                    <Select className="mt-1" value={accountId} onChange={(event) => setAccountId(event.target.value)}>
                      {accounts.map((account) => <option key={account.id} value={account.id}>{account.name} · {account.currency}</option>)}
                    </Select>
                  </label>
                  <fieldset className="flex gap-4 text-sm">
                    <label className="flex items-center gap-2"><input type="radio" name="source" checked={source === "csv"} onChange={() => setSource("csv")} /> CSV</label>
                    <label className="flex items-center gap-2"><input type="radio" name="source" checked={source === "statement"} onChange={() => setSource("statement")} /> Text statement</label>
                  </fieldset>
                  <p className="text-sm text-muted">{source === "csv" ? CSV_HINT : STATEMENT_HINT}</p>
                  <label className="block text-sm">
                    <span className="text-muted">Upload a CSV, PDF or text file (max 10 MB)</span>
                    <input className="mt-1 block w-full text-sm" type="file" accept=".csv,.pdf,.txt,application/pdf,text/csv,text/plain" onChange={(event) => { setFile(event.target.files?.[0] ?? null); if (event.target.files?.[0]) setContent(""); }} />
                  </label>
                  <p className="text-xs text-muted">PDFs must contain selectable text. Scanned statements and receipt photos are not supported yet.</p>
                  <div className="text-center text-xs text-muted">or paste statement text</div>
                  <label className="block text-sm">
                    <span className="text-muted">Filename (optional)</span>
                    <Input className="mt-1" value={filename} onChange={(event) => setFilename(event.target.value)} placeholder="statement-september.csv" />
                  </label>
                  <label className="block text-sm">
                    <span className="text-muted">Paste statement text</span>
                    <textarea className="mt-1 min-h-40 w-full border border-line bg-surface px-3 py-2 font-mono text-xs" value={content} onChange={(event) => { setContent(event.target.value); if (event.target.value) setFile(null); }} />
                  </label>
                  <Button type="submit" disabled={pending || (!file && !content.trim())}>{pending ? "Preparing..." : "Preview import"}</Button>
                </form>
                {result ? (
                  <div className="space-y-3 border border-line px-4 py-3 text-sm">
                    <p className="font-medium">{result.source} · {result.status.replaceAll("_", " ")}</p>
                    {result.status === "pending_review" ? (
                      <>
                        <p>{result.result?.row_count ?? result.result?.rows?.length ?? 0} transactions parsed · {result.result?.duplicate_count_at_preview ?? 0} possible duplicates already found</p>
                        <div className="max-h-80 space-y-2 overflow-auto">
                          {result.result?.rows?.map((row, index) => <div key={row.external_id || index} className="flex flex-wrap justify-between gap-2 border-b border-line py-2"><span>{row.date} · {row.description || row.merchant || row.type}</span><span className="font-semibold">{row.amount}</span></div>)}
                        </div>
                        <p className="text-xs text-muted">Review the rows and destination account before confirming. No balances have changed yet.</p>
                        <Button type="button" disabled={pending} onClick={() => void onCommit(result.id)}>{pending ? "Confirming..." : "Confirm and import transactions"}</Button>
                      </>
                    ) : (
                      <>
                        <p>Created {result.created_count}, skipped {result.skipped_count}, errors {result.error_count}</p>
                        {result.result?.errors?.length ? <ul className="list-disc pl-5 text-muted">{result.result.errors.map((row) => <li key={row}>{row}</li>)}</ul> : null}
                      </>
                    )}
                  </div>
                ) : null}
              </>
            )}
          </section>
        </div>
      </ContentContainer>
    </AppShell>
  );
}
