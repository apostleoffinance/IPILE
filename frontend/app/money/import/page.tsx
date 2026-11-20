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
  getAccounts,
  commitStagedImport,
  previewImport,
  previewStatementUpload,
  type Account,
  type ImportJob,
} from "@/lib/api";

const CSV_HINT = "Use a bank-exported CSV with a transaction date and amount. If your bank separates money in and money out, include debit and credit columns. A description or merchant name is helpful but optional.";
const STATEMENT_HINT = "For pasted statements, put the date, amount, description and optional reference on each line, separated by |. Example: 2026-11-01 | 25000 | Grocery shopping | REF123. Negative amounts mean money received; positive amounts mean money spent.";

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

  useEffect(() => {
    getAccounts()
      .then((rows) => {
        setAccounts(rows);
        if (rows[0]) setAccountId(rows[0].id);
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
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setPending(false);
    }
  }

  async function onCommit(jobId: string) {
    if (!accountId) return;
    setPending(true);
    setError(null);
    try {
      const committed = await commitStagedImport(jobId, accountId);
      setResult(committed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm this import.");
    } finally {
      setPending(false);
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
          description="Import a bank statement, review the parsed transactions, and confirm before anything changes your household ledger."
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
                <span className="text-muted">Upload a CSV, PDF or text file (max 10 MB)</span>
                <input
                  className="mt-1 block w-full text-sm"
                  type="file"
                  accept=".csv,.pdf,.txt,application/pdf,text/csv,text/plain"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <p className="text-xs text-muted">PDFs must contain selectable text. Scanned documents and receipt photos are not supported yet.</p>
              <div className="text-center text-xs text-muted">or paste statement text</div>
              <label className="block text-sm">
                <span className="text-muted">Filename (optional)</span>
                <Input className="mt-1" value={filename} onChange={(e) => setFilename(e.target.value)} placeholder="statement-september.csv" />
              </label>
              <label className="block text-sm">
                <span className="text-muted">Paste statement text</span>
                <textarea
                  className="mt-1 min-h-40 w-full border border-line bg-surface px-3 py-2 font-mono text-xs"
                  value={content}
                  onChange={(e) => { setContent(e.target.value); if (e.target.value) setFile(null); }}
                />
              </label>
              <Button type="button" disabled={pending || (!file && !content.trim())} onClick={() => {
                const form = document.getElementById("statement-import-form") as HTMLFormElement | null;
                form?.requestSubmit();
              }}>{pending ? "Preparing..." : "Preview import"}</Button>
              <form id="statement-import-form" onSubmit={onSubmit} />
              {result ? (
                <div className="space-y-3 border border-line px-4 py-3 text-sm">
                  <p className="font-medium">{result.source} · {result.status.replaceAll("_", " ")}</p>
                  {result.status === "pending_review" ? (
                    <>
                      <p>{result.result?.row_count ?? result.result?.rows?.length ?? 0} transactions parsed · {result.result?.duplicate_count_at_preview ?? 0} possible duplicates already found</p>
                      <div className="max-h-80 space-y-2 overflow-auto">
                        {result.result?.rows?.map((row, index) => (
                          <div key={row.external_id || index} className="flex flex-wrap justify-between gap-2 border-b border-line py-2">
                            <span>{row.date} · {row.description || row.merchant || row.type}</span>
                            <span className="font-semibold">{row.amount}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-muted">Review the rows and destination account before confirming. No balances have changed yet.</p>
                      <Button type="button" disabled={pending} onClick={() => void onCommit(result.id)}>
                        {pending ? "Confirming..." : "Confirm and import transactions"}
                      </Button>
                    </>
                  ) : (
                    <>
                      <p>Created {result.created_count}, skipped {result.skipped_count}, errors {result.error_count}</p>
                      {result.result?.errors?.length ? <ul className="list-disc pl-5 text-muted">{result.result.errors.map((row) => <li key={row}>{row}</li>)}</ul> : null}
                    </>
                  )}
                </div>
              ) : null}
            </section>

          </div>
              {review.length === 0 ? (
                <p className="text-sm text-muted">No bank alerts in the review queue.</p>
              ) : review.map((job) => (
                <div key={job.id} className="space-y-2 border border-line p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-medium">{job.filename || "Bank alert"}</div>
                    <span className="text-xs uppercase text-muted">{job.status.replaceAll("_", " ")}</span>
                  </div>
                  <div className="text-muted">From: {job.result?.sender || "Unknown sender"}</div>
                  {job.status === "rejected" ? (
                    <p className="text-sm text-muted">Not imported: {job.result?.errors?.join("; ") || "The alert could not be parsed safely."}</p>
                  ) : (
                    <>
                      {job.result?.rows?.map((row, index) => (
                        <div key={index} className="flex flex-wrap justify-between gap-2">
                          <span>{row.date} · {row.description || row.type}</span>
                          <span className="font-semibold">{row.amount}</span>
                        </div>
                      ))}
                      <Button type="button" size="sm" onClick={() => void onApprove(job.id)}>Approve into {accounts.find((account) => account.id === accountId)?.name || "selected account"}</Button>
                    </>
                  )}
                </div>
              ))}
            </section>
          </div>
        )}
      </ContentContainer>
    </AppShell>
  );
}
