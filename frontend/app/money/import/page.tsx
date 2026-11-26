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
  const [accountSection, setAccountSection] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportJob | null>(null);
  const [mailboxAddress, setMailboxAddress] = useState<string | null>(null);
  const [emailJobs, setEmailJobs] = useState<ImportJob[]>([]);
  const [reviewAccounts, setReviewAccounts] = useState<Record<string, string>>({});
  const [emailCorrections, setEmailCorrections] = useState<Record<string, { amount?: string; date?: string; type?: "income" | "expense"; description?: string; currency?: string }>>({});
  const [mailboxBusy, setMailboxBusy] = useState(false);
  const [gmail, setGmail] = useState<GmailConnectionStatus | null>(null);
  const [gmailBusy, setGmailBusy] = useState(false);
  const [gmailSyncSummary, setGmailSyncSummary] = useState<{ scanned: number; queued: number; auto_posted: number; rejected: number; ignored: number } | null>(null);
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
        ? await previewStatementUpload(accountId, file, accountSection || undefined)
        : await previewImport({ account_id: accountId, source, content, filename: filename || undefined });
      setResult(job);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not prepare this import.";
      setError(
        /HTTP 502|HTTP 503|temporarily unavailable|upstream/i.test(message)
          ? "We couldn't finish scanning your statement because the import service is temporarily unavailable. Your transactions and balances have not been changed. Please try again in a moment; if it continues, upload a smaller PDF or your bank's CSV export."
          : message,
      );
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
      setGmailSyncSummary(await syncGmail());
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
    if (!row || !accounts) return;
    const correction = emailCorrections[job.id] ?? {};
    setPending(true);
    setError(null);
    try {
      await correctEmailImport(job.id, {
        amount: correction.amount ?? String(row.amount),
        date: correction.date ?? String(row.date),
        type: correction.type ?? (row.type as "income" | "expense"),
        description: correction.description ?? String(row.description ?? ""),
        currency: correction.currency ?? row.currency ?? accounts.find((account) => account.id === reviewAccounts[job.id])?.currency,
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
                  <p className="text-xs text-muted">Google grants IPÌLẸ̀ read-only Gmail access. IPÌLẸ̀ only searches configured trusted bank-sender domains, stores extracted transaction fields rather than email bodies, and cannot send, modify or delete emails.</p>
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="outline" disabled={gmailBusy} onClick={() => void onSyncGmail()}>{gmailBusy ? "Syncing..." : "Sync now"}</Button>
                    <Button type="button" size="sm" variant="ghost" disabled={gmailBusy} onClick={() => void onDisconnectGmail()}>Disconnect Gmail</Button>
                  </div>
                  {gmail.last_sync_at ? <p className="text-xs text-muted">Last checked: {new Date(gmail.last_sync_at).toLocaleString()}</p> : null}
                  {gmailSyncSummary ? <p className="text-xs text-muted">{gmailSyncSummary.scanned} messages checked · {gmailSyncSummary.queued} awaiting review · {gmailSyncSummary.auto_posted} recorded automatically · {gmailSyncSummary.rejected} rejected</p> : null}
                  {gmail.last_error ? <p className="text-xs text-danger">{gmail.last_error}</p> : null}
                </>
              ) : (
                <>
                  <p className="text-sm font-medium">Gmail · Recommended</p>
                  <p className="text-xs text-muted">Connect the inbox where your bank alerts already arrive. Google grants read-only Gmail access; IPÌLẸ̀ processes only configured trusted bank-sender domains. You approve access through Google.</p>
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
                      {row.category_name ? <p className="text-xs text-muted sm:col-span-2">Suggested category: {row.category_name}</p> : null}
                      {job.result?.intelligence ? (
                        <div className="text-xs text-muted sm:col-span-2">
                          <p>Confidence: {job.result.intelligence.confidence_score}/100 · {job.result.intelligence.confidence_band}</p>
                          {job.result.intelligence.review_reasons.map((reason) => <p key={reason}>• {reason}</p>)}
                        </div>
                      ) : null}
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
                        <label className="block text-sm">
                          <span className="text-muted">Transaction currency</span>
                          <Select className="mt-1" value={emailCorrections[job.id]?.currency ?? row?.currency ?? (accounts.find((account) => account.id === reviewAccounts[job.id])?.currency ?? "")} onChange={(event) => setEmailCorrections((current) => ({ ...current, [job.id]: { ...current[job.id], currency: event.target.value } }))}>
                            {[...new Set(accounts.map((account) => account.currency))].map((currency) => <option key={currency} value={currency}>{currency}</option>)}
                          </Select>
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
            <h2 className="font-semibold">4. Scan and import a bank statement</h2>
            <div className="border border-line bg-surface p-3 text-sm">
              <p className="font-medium">Your statement will be scanned before anything is added.</p>
              <p className="mt-1 text-muted">Upload a bank statement PDF, CSV or image. IPÌLẸ̀ extracts transaction dates, descriptions and money in/out. Scanned PDFs are read with OCR. You will review the extracted transactions before confirming.</p>
              <p className="mt-2 text-xs text-muted">Nothing is added to your transaction history and no account balance changes until you select “Confirm and import transactions”.</p>
            </div>
            <ol className="list-decimal space-y-1 pl-5 text-sm text-muted">
              <li>Choose the household account that the statement belongs to.</li>
              <li>Upload the original statement. IPÌLẸ̀ reads selectable PDF text or scans image-only pages with OCR.</li>
              <li>Check the extracted rows, dates, amounts and duplicates.</li>
              <li>Confirm only when the preview matches your bank statement.</li>
            </ol>
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
                  {!file ? (
                    <>
                      <fieldset className="flex gap-4 text-sm">
                        <label className="flex items-center gap-2"><input type="radio" name="source" checked={source === "csv"} onChange={() => setSource("csv")} /> CSV text</label>
                        <label className="flex items-center gap-2"><input type="radio" name="source" checked={source === "statement"} onChange={() => setSource("statement")} /> Paste statement text</label>
                      </fieldset>
                      <p className="text-sm text-muted">{source === "csv" ? CSV_HINT : STATEMENT_HINT}</p>
                    </>
                  ) : (
                    <div className="border border-line bg-surface p-3 text-sm">
                      <p className="font-medium">Statement selected: {file.name}</p>
                      <p className="mt-1 text-xs text-muted">{/\.pdf$/i.test(file.name) ? "PDF selected. IPÌLẸ̀ will first read embedded text and automatically use OCR if the PDF is scanned." : /\.(png|jpe?g|webp)$/i.test(file.name) ? "Image selected. IPÌLẸ̀ will scan it with OCR." : "Structured file selected. IPÌLẸ̀ will extract its transaction rows."}</p>
                      <button type="button" className="mt-2 text-xs underline" onClick={() => { setFile(null); setResult(null); }}>Choose a different input</button>
                    </div>
                  )}
                  <label className="block text-sm">
                    <span className="text-muted">Choose your bank statement file (CSV, PDF, PNG, JPEG or WebP · max 10 MB)</span>
                    <input className="mt-1 block w-full text-sm" type="file" accept=".csv,.pdf,.txt,.png,.jpg,.jpeg,.webp,application/pdf,text/csv,text/plain,image/png,image/jpeg,image/webp" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setAccountSection(""); setResult(null); if (event.target.files?.[0]) setContent(""); }} />
                  </label>
                  <p className="text-xs text-muted">PDFs with selectable text are read directly. Image-only or scanned PDFs are automatically scanned with OCR, as are PNG, JPEG and WebP images. Files are processed privately and are not added to your ledger during scanning. Maximum file size: 10 MB; scanned PDFs: up to 12 pages.</p>
                  <div className="text-center text-xs text-muted">or paste statement text instead of uploading a file</div>
                  {!file ? (
                    <label className="block text-sm">
                      <span className="text-muted">Filename (optional)</span>
                      <Input className="mt-1" value={filename} onChange={(event) => setFilename(event.target.value)} placeholder="statement-september.csv" />
                    </label>
                  ) : null}
                  {!file ? (
                    <label className="block text-sm">
                      <span className="text-muted">Paste statement text</span>
                      <textarea className="mt-1 min-h-40 w-full border border-line bg-surface px-3 py-2 font-mono text-xs" value={content} onChange={(event) => { setContent(event.target.value); if (event.target.value) setFile(null); }} />
                    </label>
                  ) : null}
                  <Button type="submit" disabled={pending || (!file && !content.trim())}>{pending ? (file && /\.(pdf|png|jpe?g|webp)$/i.test(file.name) ? "Reading statement..." : "Preparing preview...") : "Preview import"}</Button>
                </form>
                {result ? (
                  <div className="space-y-3 border border-line px-4 py-3 text-sm">
                    <p className="font-medium">{result.source} · {result.status.replaceAll("_", " ")}</p>
                    {result.result?.extraction_method ? <p className="text-xs text-muted">{result.result.extraction_method === "pdf_ocr" || result.result.extraction_method === "image_ocr" ? "Scanned document · OCR extraction" : result.result.extraction_method === "pdf_table" || result.result.extraction_method === "pdf_text" ? "PDF text and table extraction" : result.result.extraction_method === "csv" ? "CSV transaction extraction" : "Statement text extraction"}</p> : null}
                    {result.status === "needs_section_selection" ? (
                      <>
                        <p>This statement contains more than one account. Choose which account section you want IPÌLẸ̀ to extract and review. This prevents transactions from different bank accounts being mixed together.</p>
                        <label className="block text-sm">
                          <span className="text-muted">Statement account section</span>
                          <Select className="mt-1" value={accountSection} onChange={(event) => setAccountSection(event.target.value)}>
                            <option value="">Choose an account section</option>
                            {(result.result?.available_sections ?? []).map((section) => <option key={section} value={section}>{section}</option>)}
                          </Select>
                        </label>
                        <p className="text-xs text-muted">{result.result?.row_count ?? 0} transaction rows detected across {result.result?.section_count ?? 0} account sections. No transactions have been staged or posted yet.</p>
                        <Button type="submit" disabled={pending || !file || !accountSection}>{pending ? "Extracting..." : "Continue to transaction review"}</Button>
                      </>
                    ) : result.status === "pending_review" ? (
                      <>
                        {result.result?.account_section ? <p className="font-medium">Statement section: {result.result.account_section}</p> : null}
                        <p>{result.result?.row_count ?? result.result?.rows?.length ?? 0} transactions parsed · {result.result?.duplicate_count_at_preview ?? 0} possible duplicates already found</p>
                        {result.result?.extraction_issues?.length ? <ul className="list-disc pl-5 text-xs text-muted">{result.result.extraction_issues.map((issue) => <li key={issue.code}>{issue.message}</li>)}</ul> : null}
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
