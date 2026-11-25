# Phase 0 — Security and release baseline

**Status:** In progress. This document records the interim authorization contract while Phase 0 hardening is completed. It is not a declaration that production is release-ready.

## Authorization matrix

| Capability | Owner | Partner | Member | Viewer | Advisor |
|---|---|---|---|---|---|
| Read shared accounts and transactions | Yes | Yes | Yes | Yes | Yes |
| Read personal accounts and transactions | All household records | All household records | Own records only | No | No |
| Create and edit financial records | Yes | Yes | Own transactions only | No | No |
| Void transactions | Yes | Yes | No | No | No |
| Household-wide financial aggregates and reports | Yes | Yes | Denied pending member-scoped implementation | No | No |
| Business P&L, goals, funds, obligations, calendar, income history, recurring items, alerts and notifications | Yes | Yes | Denied pending member-scoped implementation | No | No |
| CSV, TXT and PDF statement imports | Yes | Yes | No | No | No |
| Contribution agreements and records | Yes | Yes | Denied pending member-scoped implementation | No | No |
| Manage household members and invitations | Owner-controlled | Limited by owner-only endpoints | No | No | No |
| Change household settings / billing plan | Owner | No | No | No | No |

Viewer and advisor currently share the same read-only API permissions. A future explicit advisor-grant model can extend access, but neither role receives access to private records or household-wide aggregates by default.

## Enforcement rules

1. Authorization is enforced in FastAPI dependencies and query filters; frontend visibility is not an access-control boundary.
2. Every account and transaction lookup is constrained to the active household.
3. Member account and transaction reads are filtered by shared scope or the authenticated member's personal ownership.
4. Household-wide financial views remain owner/partner-only until member-scoped calculations and privacy tests exist.
5. Transaction creation validates that referenced members, categories, income sources, obligations, funds, goals and businesses belong to the active household.
6. Imports are owner/partner-only. Preview/stage does not post ledger entries; commit is explicit.
7. Contribution records remain owner/partner-only until member-specific agreement and record visibility is implemented.
8. Transactions cannot cross personal/shared account boundaries. Cross-scope transfers are intentionally rejected until they can be represented as paired ledger entries without leaking balances.

## Statement-import baseline

- CSV and text statement import paths have existing parsing, duplicate detection and balance-effect tests.
- PDF statements use selectable-text extraction through pdfplumber; the PDF preview/commit regression test is included in the CI suite.
- Unsupported, malformed or oversized uploads must fail without partial ledger posting.
- Scanned/image-only PDFs are not OCR-enabled in this phase; they must fail safely rather than produce guessed transactions.

## Database migration baseline

- Migration chain: 0016_import_mailboxes → 0017_contributions → 0018_personal_shared_finance.
- The production and staging Neon branches were observed at 0016_import_mailboxes during the Phase 0 audit. Neither environment had the contribution tables or access_scope columns at that time.
- Equivalent 0017/0018 DDL was exercised against a temporary Neon branch cloned from production; constraints and indexes were inspected, then the temporary branch was discarded. Production and staging were not modified.
- Production and staging migrations must be applied only with the matching application release and a verified backup/rollback plan.

## Phase 0 release gate

- [ ] PR #25 code review and all CI checks pass on its latest head.
- [ ] Migration chain is validated against the production baseline.
- [ ] Household isolation tests cover both directions across two households.
- [ ] Role tests cover owner, partner, member, viewer and advisor.
- [ ] Personal/shared account and transaction tests cover list, detail, update and derived views.
- [ ] CSV, text and PDF import tests pass, including no-post-before-commit and duplicate handling.
- [ ] No unresolved cross-household reference or aggregate-visibility gaps remain.
- [ ] Staging migration and application release are accepted before any production migration.

Phase 1 must not begin until every Phase 0 release-gate item is checked and the team has accepted the baseline.
