# Universal Statement Extraction Architecture

## Design decision

IPÌLẸ̀ uses one bank-agnostic statement extraction pipeline. Bank-specific
adapters are optional extensions selected only when a generic extractor cannot
reliably interpret a recurring format. The core schema, field mapping and
validation rules never depend on an institution name.

## Pipeline

1. Ingestion — identify file type, size, page count and document boundaries.
2. Document intelligence — determine whether a PDF has selectable text,
   tabular structure or scanned/image-only pages.
3. Extraction — use structured CSV/XLSX readers, PDF text/table extraction,
   or bounded OCR for scanned PDFs and images.
4. Row reconstruction — associate wrapped descriptions and references with
   their originating transaction, including page continuations.
5. Semantic field mapping — map bank-specific header labels to canonical fields.
6. Normalization — parse dates, timestamps, decimal amounts, currency,
   debit/credit direction and references without guessing.
7. Validation — validate row completeness, duplicates, statement totals,
   balance progression and source coverage.
8. Review staging — expose candidates and issues for human review. Only the
   existing explicit import commit operation may write ledger transactions.

## Canonical transaction contract

A candidate has transaction date, positive amount magnitude, explicit
debit/credit/unknown direction, description, reference, currency, transaction
and value dates, running balance, channel, source page/row, original text and
optional confidence. It is never a ledger transaction.

Unknown direction, missing amount/date, low confidence, duplicate reference or
failed reconciliation must be visible to review and never silently repaired.

## Validation statuses

- verified: all configured checks pass.
- needs_review: extraction exists but warnings or reconciliation differences
  require inspection.
- incomplete: one or more required transaction fields could not be identified.
- failed: no usable transaction rows were extracted.

## Reconciliation

When available, compare extracted debit/credit totals and counts with statement
summary totals. If opening and closing balances are present, check:
opening balance + credits - debits = closing balance (within currency minor
unit tolerance). Running balance checks are performed only when statement
ordering and balance semantics are established.

## Adapter policy

Generic extraction and aliases are tried first. Optional bank adapters may
supply layout hints or reconstruction rules, but must emit the same canonical
contracts and pass the same validation suite. Never infer bank identity solely
from a logo or filename.

## Privacy and safety

Raw statements and personally identifying information are not committed as
test fixtures. Tests use synthetic, redacted examples. Extraction output remains
household-scoped and staged; no statement parser writes to the ledger.
