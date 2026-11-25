"use client";

import { FormEvent, useEffect, useState } from "react";
import { ContentContainer } from "@/components/layouts/ContentContainer";
import { PageHeader } from "@/components/layouts/PageHeader";
import { AppShell } from "@/components/shared/AppShell";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingState } from "@/components/shared/LoadingState";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  approveReceipt,
  correctReceipt,
  getAccounts,
  getReceipts,
  previewReceipt,
  rejectReceipt,
  type Account,
  type ReceiptDocument,
} from "@/lib/api";

export default function ReceiptsPage() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [receipts, setReceipts] = useState<ReceiptDocument[]>([]);
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<string, { merchant: string; date: string; amount: string; currency: string }>>({});

  async function refresh() {
    const [accountRows, receiptRows] = await Promise.all([getAccounts(), getReceipts()]);
    const shared = accountRows.filter((account) => account.access_scope === "shared");
    setAccounts(shared);
    setReceipts(receiptRows);
    setAccountId((current) => current || shared[0]?.id || "");
    setCorrections(Object.fromEntries(receiptRows.map((receipt) => [receipt.id, {
      merchant: receipt.merchant ?? "",
      date: receipt.date ?? "",
      amount: receipt.amount ?? "",
      currency: receipt.currency ?? "",
    }])));
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file || !accountId) return;
    setBusy(true);
    setError(null);
    try {
      await previewReceipt(accountId, file);
      setFile(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process this receipt.");
    } finally {
      setBusy(false);
    }
  }

  async function onApprove(receipt: ReceiptDocument) {
    const values = corrections[receipt.id];
    setBusy(true);
    setError(null);
    try {
      await correctReceipt(receipt.id, {
        merchant: values.merchant || null,
        date: values.date || undefined,
        amount: values.amount || undefined,
        currency: values.currency || undefined,
      });
      await approveReceipt(receipt.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not approve this receipt.");
    } finally {
      setBusy(false);
    }
  }

  async function onReject(id: string) {
    setBusy(true);
    setError(null);
    try {
      await rejectReceipt(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reject this receipt.");
    } finally {
      setBusy(false);
    }
  }

  if (!accounts) return <AppShell><LoadingState /></AppShell>;

  return (
    <AppShell>
      <ContentContainer>
        <PageHeader
          eyebrow="Money"
          title="Receipt intelligence"
          description="Upload a receipt, review OCR results and confirm the expense before it enters your household ledger."
        />
        {error ? <ErrorState message={error} /> : null}
        <div className="max-w-3xl space-y-8">
          <section className="space-y-4 border border-line p-4">
            <h2 className="font-semibold">1. Scan a receipt</h2>
            <form onSubmit={onUpload} className="space-y-4">
              <label className="block text-sm">
                <span className="text-muted">Shared household account</span>
                <Select className="mt-1" value={accountId} onChange={(event) => setAccountId(event.target.value)}>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>{account.name} · {account.currency}</option>
                  ))}
                </Select>
              </label>
              <label className="block text-sm">
                <span className="text-muted">Receipt image or PDF (max 10 MB)</span>
                <input
                  className="mt-1 block w-full text-sm"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,application/pdf"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <p className="text-xs text-muted">JPEG, PNG, WEBP and PDF are supported. Files are processed in memory and are not retained.</p>
              <Button type="submit" disabled={busy || !file || !accountId}>
                {busy ? "Processing..." : "Scan receipt"}
              </Button>
            </form>
          </section>

          <section className="space-y-4">
            <h2 className="font-semibold">2. Review receipts</h2>
            {receipts.length === 0 ? (
              <p className="border border-line p-4 text-sm text-muted">No receipts have been scanned yet.</p>
            ) : receipts.map((receipt) => {
              const values = corrections[receipt.id] ?? { merchant: "", date: "", amount: "", currency: "" };
              const pending = receipt.status === "pending_review";
              return (
                <article key={receipt.id} className="space-y-3 border border-line p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{receipt.filename || "Receipt"}</p>
                      <p className="text-xs text-muted">{receipt.status.replaceAll("_", " ")} · OCR confidence {Math.round((receipt.extracted.overall_confidence ?? 0) * 100)}%</p>
                    </div>
                    <span className="text-xs text-muted">{receipt.media_type}</span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-sm">Merchant
                      <input className="mt-1 w-full border border-line bg-canvas px-3 py-2" disabled={!pending} value={values.merchant} onChange={(event) => setCorrections((current) => ({ ...current, [receipt.id]: { ...values, merchant: event.target.value } }))} />
                    </label>
                    <label className="text-sm">Date
                      <input type="date" className="mt-1 w-full border border-line bg-canvas px-3 py-2" disabled={!pending} value={values.date} onChange={(event) => setCorrections((current) => ({ ...current, [receipt.id]: { ...values, date: event.target.value } }))} />
                    </label>
                    <label className="text-sm">Total amount
                      <input inputMode="decimal" className="mt-1 w-full border border-line bg-canvas px-3 py-2" disabled={!pending} value={values.amount} onChange={(event) => setCorrections((current) => ({ ...current, [receipt.id]: { ...values, amount: event.target.value } }))} />
                    </label>
                    <label className="text-sm">Currency
                      <input maxLength={3} className="mt-1 w-full border border-line bg-canvas px-3 py-2 uppercase" disabled={!pending} value={values.currency} onChange={(event) => setCorrections((current) => ({ ...current, [receipt.id]: { ...values, currency: event.target.value.toUpperCase() } }))} />
                    </label>
                  </div>
                  {receipt.extracted.warnings?.length ? (
                    <ul className="list-disc space-y-1 pl-5 text-xs text-muted">
                      {receipt.extracted.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                    </ul>
                  ) : null}
                  {pending ? (
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" disabled={busy} onClick={() => void onApprove(receipt)}>Confirm expense</Button>
                      <Button type="button" variant="outline" disabled={busy} onClick={() => void onReject(receipt.id)}>Reject</Button>
                    </div>
                  ) : receipt.transaction_id ? (
                    <p className="text-xs text-muted">Linked transaction: {receipt.transaction_id}</p>
                  ) : null}
                </article>
              );
            })}
          </section>
        </div>
      </ContentContainer>
    </AppShell>
  );
}
