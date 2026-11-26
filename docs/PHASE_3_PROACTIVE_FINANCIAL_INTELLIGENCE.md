# Phase 3 — Proactive Financial Intelligence

**Status:** Implementation in progress  
**Predecessor:** Phase 2 completion — recurring and anomaly intelligence

## Objective

Turn verified Phase 2 transaction patterns into timely, explainable household alerts, and keep the financial workspace current as ledger activity changes.

## Delivered scope

- Persist upcoming and apparently missed recurring-payment signals as household alerts.
- Persist unusually large transaction signals with a direct reference to the source transaction.
- Create in-app notifications from new open intelligence alerts.
- Deduplicate alerts by household, signal type, related entity and period key.
- Do not reopen alerts a household member has already read or resolved.
- Resolve stale recurring reminders when the expected date changes, and resolve anomaly alerts when the source transaction is corrected, voided or ages out of the detection window.
- Refresh intelligence on daily automation, recognized income, shared manual transaction creation/update/void, and imported transaction commits.
- Recompute allocation runs when additional income arrives in an already-processed period; incrementally top up fund transfers by the unfunded difference without automatically withdrawing funds when targets fall.
- Recompute allocations after shared income edits or voids, and after imports containing income.
- Keep review-only bank alerts out of the ledger and intelligence pipeline until approval.
- Surface unread proactive alerts on the Insights page and link users to the Inbox for review.
- Use only shared, cleared/reconciled transactions for household-level alerts.

## Safety invariants

- Alerts are advisory. They never post transactions, change balances, block payments or label activity as fraud.
- All comparisons remain within the same account, currency, transaction direction and category.
- Personal-scope transactions are excluded from household-level intelligence.
- Existing review-everything defaults and bank-alert auto-posting gates remain unchanged.
- Alert generation is idempotent; repeated daily ticks do not create duplicate notifications.
- No new external email permissions, production secrets or production deployment are introduced.

## Acceptance tests

- A third consistent monthly transaction creates one upcoming recurring alert and one in-app notification.
- Re-running daily automation does not duplicate that notification.
- A transaction materially above its same-payee historical median creates an anomaly alert and notification.
- Additional same-period income refreshes recognized income and allocation amounts without duplicate fund transfers; fund contributions increase only by the incremental difference.
- Voiding/correcting the source transaction resolves its open anomaly alert.
- Imported transactions invoke the same intelligence refresh path after they are committed.
- The Insights page displays unread proactive notifications and routes to the Inbox.
- Existing multi-household, backend, frontend, Worker and migration checks remain green.
