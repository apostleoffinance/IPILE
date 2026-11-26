# IPÌLẸ̀ production readiness and operations

## Canonical environments

| Environment | API | Render service |
|---|---|---|
| Staging | https://ipile-staging-api-v2.onrender.com | `srv-dc03v37f3r2c738k4hi0` |
| Production | https://ipile-bmfz.onrender.com | `srv-damvst142hec73cmkbv0` |

The legacy `ipile-staging-api` service (`srv-dc03n7uc6qcc73b299vg`) is not referenced by the current staging deployment workflow. Do not use it as the staging release target; review and retire it separately after confirming no clients depend on it.

## Automated release and runtime checks

- `.github/workflows/ci.yml` runs backend lint/tests, frontend typecheck/unit/build, migration smoke, and multi-household release acceptance.
- `.github/workflows/production-operations.yml` checks staging and production liveness, database connectivity, Alembic migration readiness, request IDs, exact backend release-SHA parity, and the production web Worker every 15 minutes (and on pull requests).
- `GET /api/v1/health/live` checks process liveness only.
- `GET /api/v1/health` checks PostgreSQL connectivity and exact Alembic head parity, and exposes the non-secret `RENDER_GIT_COMMIT` release SHA. A 503 or staging/production SHA mismatch is a release blocker.

## Daily household automation

The Cloudflare inbound-email Worker already runs every five minutes. It now also calls `POST /api/v1/automation/cron/daily`; the API computes each household's local date and uses the unique scheduler tick key to make repeated calls safe.

Before enabling this schedule in either environment:

1. Generate a distinct high-entropy secret for staging and production.
2. Set `AUTOMATION_CRON_SECRET` on the matching Render API service.
3. Set `AUTOMATION_CRON_SECRET` on the matching Cloudflare Worker environment (`ipile-inbound-email` for staging, `ipile-inbound-email-production` for production).
4. Deploy the matching Worker environment.
5. Confirm successful scheduler requests in Cloudflare Worker observability and Render application logs. The endpoint returns household, processed, skipped and failed counts.
6. Confirm a second invocation for the same local date reports skipped ticks and creates no duplicate allocations or notifications.

The scheduler does not post bank-alert imports or change bank-alert automation preferences. It runs the existing daily household automation chain (due-date checks, budgets, Safe to Spend, financial intelligence and notification synchronization).

## Safe production smoke-test procedure

Use a dedicated internal test household and test Gmail inbox. Never use the founding/primary household for destructive smoke tests.

- Authentication: register/login/logout and verify session cookies are HttpOnly, Secure and same-site; verify a second test household cannot read the first household's accounts or transactions.
- Transactions: create a clearly labelled test transaction, edit it, verify balances and audit trail, then void it and verify the reversal. Do not test with real bank transactions.
- Gmail: connect a dedicated inbox with read-only Gmail scope; send/receive a controlled bank-alert fixture from an allow-listed sender; verify it appears as pending review under review-everything mode; approve it once; replay the same message and confirm deduplication.
- Recurring payments: add at least three cleared test transactions on a consistent cadence; verify one upcoming/missed alert and one notification. Re-run daily automation and verify no duplicates.
- Anomalies: establish at least four historical comparable test transactions, add one unusually large transaction, verify one advisory alert, then correct/void the test transaction and verify alert resolution.
- Notifications: verify unread creation, mark-read behavior, and that resolved alerts close their unread notifications.
- Allocation: record test income, verify allocation totals and fund contributions; add more same-period income and verify only the incremental fund top-up is applied.

Automated tests cover tenancy, import deduplication, recurring/anomaly detection, notification idempotency/resolution, allocation refresh and migration readiness. Real OAuth and bank sender delivery still require the dedicated live test inbox described above.

## Monitoring runbook

### Every 15 minutes

Review the GitHub Actions **IPÌLẸ̀ runtime health** workflow. Any failed staging or production readiness check is an incident to investigate before further rollout.

### Render

For both canonical API services, inspect:
- Application logs for `ERROR`, `Traceback`, `request_failed`, database connection failures, and repeated 5xx responses.
- Events for `server_failed`, `server_restarted`, failed deploys and out-of-memory terminations.
- Deploy metadata for the same main commit SHA and successful live status.

Do not include request bodies, cookies, OAuth tokens, bank-alert content or account data in incident reports.

### Cloudflare

Inspect Worker observability for:
- `ipile-inbound-email` and `ipile-inbound-email-production` email delivery failures.
- Scheduled event failures and non-2xx Gmail/daily automation requests.
- Worker exceptions and API proxy 5xx responses.

### Error reporting

The backend supports Sentry, but reporting is disabled unless `SENTRY_DSN` is configured. If enabling it, configure separate staging and production DSNs, keep `send_default_pii=false`, and preserve the existing event scrubbing. Never paste DSNs or credentials into Git.

## Deployment evidence captured 2026-11-26

- Staging and production Render APIs both show the Phase 3 merge commit `65fc76f15ac8d44f583ada2fe7d3d4b26f5155b5` as live.
- Both services completed deploy events successfully and application startup was observed.
- The production API had a prior `server_failed` event at 09:41 UTC with `oomKilled.memoryLimit=512Mi`; the later deployment was live. Continue watching memory/restart events before treating production as fully stable.
- No production transactions were created or modified during this inspection.
