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
  createImportMailbox,
  getAccounts,
  getImportReview,
  importCsv,
  importStatement,
  uploadStatement,
  type Account,
  type ImportJob,
} from "@/lib/api";

const CSV_HINT = "CSV columns: date and amount, or date plus debit/credit. Optional: type, description/narration, merchant, category, external_id.";
const STATEMENT_HINT = "Supported text layout: date|amount|narrative|reference. Negative amount is treated as income; positive as expense.";

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
  const [mailbox, setMailbox] = useState<string | null>(null);
  const [review, setReview] = useState<ImportJob[]>([]);
  const [mailboxPending, setMailboxPending] = useState(false);

  async function refreshReview() {
    try {
      setReview(await getImportReview());
    } catch {
      // Inbound email may not be configured yet; manual statement imports remain available.
    }
  }

  useEffect(() => {
    getAccounts()
      .then((rows) => {
        setAccounts(rows);
        if (rows[0]) setAccountId(rows[0].id);
      })
      .catch((err: Error) => setError(err.message));
    void refreshReview();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!accountId || (!file && !content.trim())) return;
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const job = file
        ? await uploadStatement(accountId, file)
        : source === "csv"
          ? await importCsv({ account_id: accountId, content, filename: filename || undefined })
          : await importStatement({ account_id: accountId, content, filename: filename || undefined });
      setResult(job);
      setContent("");
      setFile(null);
      setFilename("");
      await refreshReview();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setPending(false);
    }
  }

  async function onCreateMailbox() {
    setMailboxPending(true);
    setError(null);
    try {
      const created = await createImportMailbox();
      setMailbox(created.address);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create an import address.");
    } finally {
      setMailboxPending(false);
    }
  }

  async function onApprove(jobId: string) {
    if (!accountId) return;
    setError(null);
    try {
      await approveEmailImport(jobId, accountId);
      await refreshReview();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve this bank alert.");
    }
  }

  if (!accounts) {
    return <AppShell><LoadingState /></AppShell>;
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Money"
          title="Import transactions"
          description="Bring bank statement data into your household ledger, then review forwarded bank alerts before they affect your balances."
        />
        {error ? <ErrorState message={error} /> : null}
        {accounts.length === 0 ? (
          <EmptyState title="Add an account first" body="Imports post against a household bank or cash account." />
        ) : (
          <div className="max-w-3xl space-y-8">
            <section className="space-y-4 border border-line p-4">
              <h2 className="font-semibold">1. Import a bank statement</h2>
              <label className="block text-sm">
                <span className="text-muted">Destination account</span>
                <Select className="mt-1" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                  {accounts.map((account) => <option key={account.id} value={account.id}>{account.name} · {account.currency}</option>)}
                </Select>
              </label>
              <fieldset className="flex gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input type="radio" name="source" checked={source === "csv"} onChange={() => setSource("csv")} /> CSV
                </label>
                <label className="flex items-center gap-2">
                  <input type="radio" name="source" checked={source === "statement"} onChange={() => setSource("statement")} /> Text statement
                </label>
              </fieldset>
              <p className="text-sm text-muted">{source === "csv" ? CSV_HINT : STATEMENT_HINT}</p>
              <label className="block text-sm">
                <span className="text-muted">Upload CSV, PDF or TXT (max 10 MB)</span>
                <input
                  className="mt-1 block w-full text-sm"
                  type="file"
                  accept=".csv,.pdf,.txt,application/pdf,text/csv,text/plain"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <p className="text-xs text-muted">PDF support currently requires selectable text. Scanned/image-only PDFs need OCR and are not yet supported.</p>
              <div className="text-center text-xs text-muted">or paste statement contents</div>
              <label className="block text-sm">
                <span className="text-muted">Filename (optional)</span>
                <Input className="mt-1" value={filename} onChange={(e) => setFilename(e.target.value)} placeholder="statement-september.csv" />
              </label>
              <label className="block text-sm">
                <span className="text-muted">Paste file contents</span>
                <textarea
                  className="mt-1 min-h-40 w-full border border-line bg-surface px-3 py-2 font-mono text-xs"
                  value={content}
                  onChange={(e) => { setContent(e.target.value); if (e.target.value) setFile(null); }}
                />
              </label>
              <Button type="button" disabled={pending || (!file && !content.trim())} onClick={() => {
                const form = document.getElementById("statement-import-form") as HTMLFormElement | null;
                form?.requestSubmit();
              }}>{pending ? "Importing..." : "Import statement"}</Button>
              <form id="statement-import-form" onSubmit={onSubmit} />
              {result ? (
                <div className="border border-line px-4 py-3 text-sm">
                  <p>{result.source} · {result.status}: created {result.created_count}, skipped {result.skipped_count}, errors {result.error_count}</p>
                  {result.result?.errors?.length ? <ul className="mt-2 list-disc pl-5 text-muted">{result.result.errors.map((row) => <li key={row}>{row}</li>)}</ul> : null}
                </div>
              ) : null}
            </section>

            <section className="space-y-3 border border-line p-4">
              <h2 className="font-semibold">2. Forward bank alert emails</h2>
              <p className="text-sm text-muted">Create a private household address and forward bank transaction alerts to it. Alerts are parsed into a review queue; they do not change balances until approved.</p>
              <Button type="button" variant="outline" disabled={mailboxPending} onClick={onCreateMailbox}>
                {mailboxPending ? "Creating..." : "Generate household import address"}
              </Button>
              {mailbox ? <div className="break-all rounded border border-line bg-surface p-3 font-mono text-sm">{mailbox}</div> : null}
              <p className="text-xs text-muted">This requires inbound email routing and webhook credentials to be configured by the IPÌLẸ̀ operator. Generating a new address invalidates the previous one.</p>
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">3. Bank alert review queue</h2>
                <Button type="button" variant="ghost" onClick={() => void refreshReview()}>Refresh</Button>
              </div>
              {review.length === 0 ? (
                <p className="text-sm text-muted">No bank alerts waiting for review.</p>
              ) : review.map((job) => (
                <div key={job.id} className="space-y-2 border border-line p-4 text-sm">
                  <div className="font-medium">{job.filename || "Bank alert"}</div>
                  <div className="text-muted">From: {job.result?.sender || "Unknown sender"}</div>
                  {job.result?.rows?.map((row, index) => (
                    <div key={index} className="flex flex-wrap justify-between gap-2">
                      <span>{row.date} · {row.description || row.type}</span>
                      <span className="font-semibold">{row.amount}</span>
                    </div>
                  ))}
                  <Button type="button" size="sm" onClick={() => void onApprove(job.id)}>Approve into {accounts.find((account) => account.id === accountId)?.name || "selected account"}</Button>
                </div>
              ))}
            </section>
          </div>
        )}
      </ContentContainer>
    </AppShell>
  );
}
