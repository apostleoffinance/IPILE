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
  importCsv,
  importStatement,
  type Account,
  type ImportJob,
} from "@/lib/api";

const CSV_HINT =
  "Header required: date, amount, external_id. Optional: type, description, merchant, category.";
const STATEMENT_HINT =
  "Lines: date|amount|narrative|reference. Negative amount → income; positive → expense.";

export default function ImportPage() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [accountId, setAccountId] = useState("");
  const [source, setSource] = useState<"csv" | "statement">("csv");
  const [content, setContent] = useState("");
  const [filename, setFilename] = useState("");
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
    if (!accountId || !content.trim()) return;
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        account_id: accountId,
        content,
        filename: filename || undefined,
      };
      const job = source === "csv" ? await importCsv(body) : await importStatement(body);
      setResult(job);
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setPending(false);
    }
  }

  if (!accounts) {
    return (
      <AppShell>
        <LoadingState />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Money"
          title="Import"
          description="Normalize CSV or statement text into household transactions."
        />
        {error ? <ErrorState message={error} /> : null}
        {accounts.length === 0 ? (
          <EmptyState
            title="Add an account first"
            body="Imports post against a household bank or cash account."
          />
        ) : (
          <form className="max-w-2xl space-y-4" onSubmit={onSubmit}>
            <label className="block text-sm">
              <span className="text-muted">Account</span>
              <Select
                className="mt-1"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
              >
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </Select>
            </label>
            <fieldset className="flex gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="source"
                  checked={source === "csv"}
                  onChange={() => setSource("csv")}
                />
                CSV
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="source"
                  checked={source === "statement"}
                  onChange={() => setSource("statement")}
                />
                Bank statement
              </label>
            </fieldset>
            <p className="text-sm text-muted">{source === "csv" ? CSV_HINT : STATEMENT_HINT}</p>
            <label className="block text-sm">
              <span className="text-muted">Filename (optional)</span>
              <Input
                className="mt-1"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder={source === "csv" ? "sept.csv" : "statement.txt"}
              />
            </label>
            <label className="block text-sm">
              <span className="text-muted">Paste file contents</span>
              <textarea
                className="mt-1 min-h-48 w-full border border-line bg-surface px-3 py-2 font-mono text-xs"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                required
              />
            </label>
            <Button type="submit" disabled={pending}>
              {pending ? "Importing..." : "Import"}
            </Button>
          </form>
        )}
        {result ? (
          <div className="max-w-2xl border border-line px-4 py-3 text-sm">
            <p>
              {result.source} · {result.status}: created {result.created_count}, skipped{" "}
              {result.skipped_count}, errors {result.error_count}
            </p>
            {result.result?.errors?.length ? (
              <ul className="mt-2 list-disc pl-5 text-muted">
                {result.result.errors.map((row) => (
                  <li key={row}>{row}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </ContentContainer>
    </AppShell>
  );
}
