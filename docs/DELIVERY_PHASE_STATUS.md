# IPÌLẸ̀ delivery extensions

This tracker records the additional delivery milestones requested after the original
implementation roadmap. It does not rename or overwrite the original roadmap's Phases 0–15.

| Delivery phase | Scope | Status | Gate |
|---|---|---|---|
| 4 | Receipt intelligence and OCR | in progress | Must pass backend, frontend, migration, security and acceptance checks and merge before Phase 5 starts |
| 5 | Reconciliation and bank connectivity | locked | May start only after Delivery Phase 4 is merged |

## Execution rules

- Implement one delivery phase at a time.
- Never post OCR output to the ledger without explicit household owner/partner approval.
- Expected data and imported data remain distinct from cleared/verified money until approved.
- Do not store uploaded receipt images in the application database or logs.
- Bank connectivity must use provider adapters and server-side credentials; never collect bank login passwords.
- Bank sync and statement ingestion must be idempotent and must not overwrite manually entered transactions.
- No live bank provider is assumed to be configured by a passing unit test.

## Delivery Phase 4 — Receipt intelligence and OCR

Definition of done:

- JPEG, PNG, WEBP and PDF receipts are accepted within configured upload limits.
- OCR extracts merchant, date, total, currency and field confidence where readable.
- Ambiguous or missing fields are explicitly flagged and can be corrected by the user.
- Household-scoped duplicate detection prevents repeated uploads from creating duplicate receipt records.
- OCR processing does not persist the original file or post a transaction.
- An authorized owner/partner can approve or reject a receipt.
- Approval creates one expense transaction and applies the balance effect exactly once.
- Shared/personal account boundaries and household isolation are enforced.
- Migration, backend tests, frontend checks, lint and dependency audit pass in CI.
- Operational documentation explains OCR runtime dependencies and data retention.

## Delivery Phase 5 — Reconciliation and bank connectivity

This phase remains locked until Delivery Phase 4 is merged. Its detailed scope will be established
against the merged receipt/import architecture before implementation. It must include statement
reconciliation, deterministic matching, conflict review, idempotent provider sync, account
connection lifecycle, consent/revocation, token security, auditability and provider sandbox tests.
