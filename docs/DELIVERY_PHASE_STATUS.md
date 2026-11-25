# IPÌLẸ̀ delivery extensions

This tracker records delivery milestones added after the original roadmap. Original roadmap phases 0–15 retain their existing numbering.

| Delivery phase | Scope | Status |
|---|---|---|
| 4 | Receipt intelligence and OCR | merged |
| 5 | Reconciliation and bank connectivity | implementation in progress |

## Phase 4

Receipt intelligence and OCR merged to main in commit `d19e14d6e24f9718ae53b1af41d3a30c712992ce`.

## Phase 5 definition of done

- CSV and selectable-text PDF statements can be previewed without ledger mutation.
- Opening/closing statement arithmetic is reported where calculable.
- Duplicate statement and provider transaction references are idempotently skipped.
- Deterministic match suggestions and conflict review are available; no automatic matching.
- Explicit manual match, post, ignore and session completion actions are household-scoped.
- Mono Connect initiation, authenticated/idempotent webhooks, data-status lifecycle, transaction sync, re-authorisation and disconnect are implemented.
- Provider IDs are encrypted; provider balances remain separate from ledger balances.
- Personal accounts are excluded; only shared household accounts may be linked/reconciled.
- Backend/frontend tests, lint, dependency audit and release acceptance pass.
- No production migration or live bank connection occurs without deployment-owner approval.
