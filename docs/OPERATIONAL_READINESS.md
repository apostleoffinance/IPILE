# Operational readiness — IPÌLẸ̀

**Purpose:** prove that the service can be operated safely, recover household data, detect failures, handle support, and meet its stated privacy and billing obligations.

This document distinguishes implementation from live operational evidence. A green build is not proof of a backup, restore, alert delivery, legal compliance, or payment settlement. The production observations below were recorded on 2026-11-19 and have not been independently reverified for this Phase 6 review; treat them as historical until an operator refreshes the evidence.

## Current production observations (2026-11-19)

| Area | Observed evidence | Status |
|---|---|---|
| API hosting | Render service `IPILE`, Free plan, one instance, public HTTPS URL, auto-deploy from `main` | Running; capacity/reliability review required |
| Database | Neon project `ipile` (`rough-wave-86185521`), AWS `us-east-2`, PostgreSQL 18, default `production` branch, database `neondb`. Render production environment now uses the Neon `ipile_app` runtime role and separate owner/migration URL. Render deployment `dep-dbvi2ol9el5s739qsdl0` is live; migrations `0001` through `0016` completed; Render HEAD readiness probe returned 200. | **Connected and migrated**; live public GET probe still to be independently verified |
| Backup schedule | One manual Neon snapshot (`ipile-before-first-migration-2026-11-19`) was created before initial schema migration. Neon reports 6-hour history retention. Scheduled snapshot creation is unavailable for this project on its current plan; no daily schedule or post-migration snapshot is configured. | **Release blocker** |
| Restore | No isolated restore from the production snapshot has been completed. Current production schema has 45 tables, migration head `0016_import_mailboxes`, and zero households/users/accounts/transactions. | **Release blocker** |
| Application monitoring | Render provides service logs, deploy events and resource metrics. API middleware emits request IDs and structured request/error logs. | Partially implemented |
| External error reporting | Optional Sentry integration and sensitive-data scrubbing are implemented; no production DSN or alert delivery evidence has been verified. | **Release blocker until configured and test alert delivered** |
| Privacy | Household isolation, export, soft-delete, session security and audit logging are implemented. A public privacy notice and operational retention schedule are required. | Documentation/action required |
| Support | Authenticated support-ticket creation and per-user ticket listing exist. No staffed response SLA or customer-facing escalation channel has been verified. | Operational owner required |
| Billing | Household plan labels and a shared-secret webhook stub exist. No Paystack/Stripe checkout, provider signature verification, subscription lifecycle, reconciliation or refund flow is implemented. | **Paid billing is not ready** |

## 1. Database durability and backups

### Required controls

- Use a managed PostgreSQL production database with encrypted storage and TLS connections.
- Confirm the database referenced by the production service's `DATABASE_URL`; never copy its value into tickets, logs, CI output or documentation.
- Enable automated daily backups at minimum and point-in-time recovery (PITR) where supported.
- Target pilot recovery objectives: **RPO ≤ 24 hours** and **RTO ≤ 4 hours**. Tighten these before general availability.
- Retain at least 7 daily restore points and 4 weekly restore points, subject to provider capability and data-minimization requirements.
- Restrict backup access to designated operators; record access and restore activity.
- Back up application configuration and secrets separately in an approved secret manager. Do not store secrets in the database dump or repository.
- Alert on backup failures, missing backup points, storage exhaustion and failed restores.

### Restore drill

Run only against an isolated restore target, never over the live production database.

1. Record source database identity (provider, project/instance, region), backup timestamp and backup identifier.
2. Restore to a new isolated database/branch.
3. Run schema/migration verification and read-only smoke checks.
4. Compare table counts and representative household/account/transaction totals against a pre-backup manifest. Do not export customer PII into CI artifacts.
5. Verify two-household isolation against the restored dataset.
6. Start a staging API against the restored database and verify readiness, login, account listing, transaction listing and export.
7. Record RPO, elapsed restore time, operator, evidence links, deviations and cleanup.
8. Destroy the temporary restore target after evidence has been recorded and approved.

### Required evidence

- Provider backup policy screenshot/export.
- Most recent successful backup timestamp and retention expiry.
- Successful isolated restore run identifier.
- Migration head and schema verification output.
- RPO/RTO calculation and sign-off.

A local `pg_dump` command is a useful operator tool but does not prove production backups are configured.

## 2. Monitoring and error reporting

### Existing controls

- Every API response carries `X-Request-Id`.
- Request middleware logs method, path, status and duration; unhandled exceptions include stack traces.
- Render service logs, deploy events, CPU and memory metrics are available.

### Required production alerts

| Signal | Trigger | Response |
|---|---|---|
| Availability | Readiness fails for 2 consecutive checks | Page operator; inspect DB and migrations |
| Server errors | 5xx rate > 2% for 5 minutes or 5xx spike | Triage by request ID |
| Latency | p95 API latency > 1.5s for 10 minutes | Inspect slow queries and resource pressure |
| Database | Connection failures, pool exhaustion, storage > 80% | Page operator |
| Backups | Expected backup missing or failed | Page operator; do not wait for restore request |
| Deployments | Build/deploy failure or unhealthy post-deploy readiness | Roll back or stop rollout |
| Security | Repeated auth failures, rate-limit spikes, unexpected admin actions | Security review |

Thresholds are initial pilot defaults and must be tuned from real traffic.

### Error reporting requirements

- Configure the optional Sentry integration with `SENTRY_DSN` and a low `SENTRY_TRACES_SAMPLE_RATE` before public release.
- Send unhandled exceptions and release/environment identifiers.
- Do not send request bodies, passwords, session cookies, CSRF tokens, payment secrets, bank statements, account numbers or financial descriptions.
- Disable default user/PII capture. Scrub sensitive headers, query strings and request context.
- Set alert routing to a monitored operator channel; verify an actual test alert reaches its recipient.
- Document access, retention and deletion for error events.

## 3. Privacy and data governance

- Publish a privacy notice before public onboarding.
- Explain controller/operator identity, categories of data, purposes, lawful basis, processors, international transfers, retention, user rights, security contact and complaint route.
- Collect only data required to provide household finance features.
- Do not collect or store bank login credentials; statement files/imports and financial records are sensitive.
- Use HTTPS in transit, managed database encryption at rest, least-privilege database access and restricted operator access.
- Keep audit events separate from diagnostic logs; avoid sensitive payloads in either.
- Define retention and deletion for accounts, transactions, imports, support tickets, audit logs, backups and error reports.
- Ensure household export and deletion workflows are documented. Soft deletion is not the same as immediate erasure from backups.
- Review vendors and cross-border processing before production launch.
- Complete a Nigeria Data Protection Act / NDPC compliance review with qualified counsel or a privacy professional. This document is not legal advice or a compliance certification.

## 4. Support operations

### Existing product capability

Authenticated users can create support tickets and view their own tickets. Ticket records are user-scoped.

### Required before launch

- Assign a named support owner and backup owner.
- Publish a monitored support email or in-product contact route.
- Define severity and response targets (suggested pilot: critical access/data incident acknowledgement within 4 business hours; normal questions within 2 business days).
- Provide ticket status, ownership, response history and escalation process.
- Never ask customers to send passwords, one-time codes, full bank credentials or unredacted statements through ordinary email.
- Create incident runbooks for account lockout, suspected cross-household exposure, incorrect balances, import errors and data deletion requests.
- Test a support request end-to-end and confirm an operator receives and responds to it.

## 5. Billing and payments

The current plan endpoint allows a household owner to change a plan label. The webhook is a provider-agnostic shared-secret stub. Neither is proof of payment.

Before charging customers, implement and verify:

- Paystack or Stripe checkout with server-created payment sessions.
- Provider signature verification over the raw webhook body.
- Event-id idempotency and replay protection.
- Subscription lifecycle handling: pending, active, past due, canceled, expired and refunded.
- Server-authoritative plan entitlements; clients cannot grant paid access.
- Payment reconciliation against provider transactions.
- Receipts, failed-payment handling, cancellations and refunds.
- Currency, tax, pricing and renewal disclosures.
- Billing audit trail and household-level authorization.
- Sandbox-to-live cutover checklist and a low-value live transaction/reversal test.

Until then, keep the product in a clearly identified pilot/free state and do not represent the Family plan as a paid subscription.

## 6. Release decision

A release is **GO** only when:

- [ ] Production database identity is confirmed and owned by the IPÌLẸ̀ production service.
- [ ] Automated backups and retention are enabled and evidenced.
- [ ] An isolated restore drill passes and meets RPO/RTO.
- [ ] Availability/error/latency/database/backup alerts reach a monitored owner.
- [ ] Sentry is configured with sensitive-data scrubbing and a test alert is received by the on-call owner.
- [ ] Privacy notice and retention schedule are approved and published.
- [ ] Support owner, contact channel and response targets are active.
- [ ] Billing is either fully implemented and tested or paid features remain disabled and clearly described as pilot-only.
- [ ] Release acceptance suite passes against two or more independent households.
- [ ] No open critical/high security, privacy, data-integrity or isolation defects remain.

## Evidence log

| Date | Control | Evidence | Result | Owner |
|---|---|---|---|---|
| 2026-11-19 | Render service inspection | One Free web service; no Render Postgres instance in connected workspace | Observed | Release engineering |
| 2026-11-19 | Application telemetry | Request IDs and structured logs in code; Render logs/events/metrics accessible | Partial | Release engineering |
| 2026-11-19 | Neon production connection | Project `ipile`, `rough-wave-86185521`, branch `production`, database `neondb`; Render runtime/migration URLs configured without exposing secrets | Connected | Release engineering |
| 2026-11-19 | Database migration | Render deployment `dep-dbvi2ol9el5s739qsdl0` live; Alembic `0001`–`0016`; root HEAD readiness returned 200; seed disabled; 45 tables; zero household data | Passed | Release engineering |
| 2026-11-19 | Runtime database privileges | `ipile_app` can read household data, has schema USAGE, and does not have schema CREATE; default DML/sequence privileges configured for migration-created objects | Passed | Database operator |
| 2026-11-19 | Pre-migration snapshot | Manual snapshot `ipile-before-first-migration-2026-11-19` created before schema bootstrap | Created; not a post-migration restore test | Database operator |
| 2026-11-19 | Neon scheduled backups | Scheduled snapshot API returned `backup schedule creation is not enabled for this project`; project history retention is 6 hours | **Not passed** | Database operator |
| 2026-11-19 | Backup/restore | No IPÌLẸ̀ backup schedule or restore evidence verified | **Not passed** | Database operator |
| 2026-11-19 | Billing | Plan switching and webhook stub only | **Not paid-ready** | Product/finance |


## 7. Deployment governance and traffic controls

### Deployment workflow

The repository's Cloudflare production workflow is manual-only, checks out `main`, serializes production deployments, runs dependency audit, typecheck, frontend tests, Worker build and dry-run, then deploys once. It targets the GitHub Actions environment named `production`.

Repository administrators must configure that environment with:
- Required reviewer approval before a deployment job can access production secrets.
- Deployment branch restrictions limited to `main`.
- Environment-scoped `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets.
- A monitored owner responsible for approval and rollback.

The workflow file cannot enforce required reviewers by itself. Confirm the environment settings in GitHub before enabling a production deployment.

### Backend deployment guard

The 2026-11-19 Render observation recorded the API service as auto-deploying from `main`, and the backend Dockerfile runs `alembic upgrade head` during container startup. Both settings must be reverified before merging changes to `main`. If Render still auto-deploys from `main`, a merge can trigger a production backend deployment and migrations; disable auto-deploy or use an approved release process before merging code that must not reach production.

### Authentication rate limiting

The current API rate limiter stores counters in process memory and derives client identity from proxy-forwarded headers. This is not a durable multi-instance limiter, and forwarded headers are only trustworthy when the origin is protected so clients cannot spoof them. Before scaling beyond one trusted application instance or exposing authentication endpoints to untrusted direct-origin traffic:
- Establish and document the trusted proxy/origin boundary.
- Use a shared rate-limit store or managed edge rate limiting with explicit per-action policies.
- Test spoofed forwarding headers, parallel requests, process restarts and multi-instance behavior.
- Confirm 429 responses and Retry-After behavior without logging credentials or request payloads.

These controls remain release-readiness items; CI does not prove the live Render, GitHub environment, backup, monitoring or proxy configuration.


## 8. Phase 6 live verification — 2026-11-25

This section supersedes older observations only where it explicitly records a newer observation. It is an evidence log, not a GO decision.

| Control | Live evidence on 2026-11-25 | Result |
|---|---|---|
| Render auto-deploy | Production `IPILE`, staging `ipile-staging-api-v2`, and legacy staging `ipile-staging-api` all report `autoDeploy=no` / `autoDeployTrigger=off`. | **Passed** |
| Staging release | Render deploy `dep-dc3hc8afngtc73e0osv0` for commit `a830a85cd9a3500483289614892c077e93ae0e16` reached `live`; build and deploy events succeeded. | **Passed** |
| Staging migration | Staging Neon branch `br-bitter-term-bex566zc` reports `0022_bank_reconciliation`; startup logs show migrations 0017–0022 completed. | **Passed** |
| Production migration boundary | Production Neon branch `br-mute-rice-bedagamw` remains at `0016_import_mailboxes`. No production migration or deploy was triggered. | **Passed — unchanged** |
| Production API health | Render service is configured as live, but the connected inspection path could not retrieve an external HTTP response from the public health endpoints. | **Not independently verified** |
| Render health check | Service metadata reports no configured Render `healthCheckPath`. | **Action required** |
| Automated backup schedule | Neon snapshot schedule is empty. Attempt to configure a daily schedule returned `backup schedule creation is not enabled for this project`. | **Blocked by current Neon project/plan** |
| Manual snapshot capacity | Project has one manual snapshot, `ipile-before-first-migration-2026-11-19`. A new snapshot request returned `snapshots limit exceeded`. Existing snapshot predates schema bootstrap and is not a usable current recovery point. | **Release blocker** |
| Restore drill | Existing pre-migration snapshot restored successfully to isolated branch `ipile-restore-drill-2026-11-25`, but the restored branch contains zero public tables and no `alembic_version`. This proves the provider restore operation only; it does **not** prove recovery of current application data/schema. | **Failed acceptance / release blocker** |
| Safety clone | A no-compute clone of the current production branch was created and reached `ready`: `ipile-prod-safety-clone-2026-11-25` (`br-mute-dawn-be0f06fq`). It is an isolated copy, not a scheduled backup or tested application restore. | **Partial mitigation only** |
| Branch protection | Neon refused to protect the production branch because the current plan has reached its protected-branch limit. | **Blocked by plan quota** |
| GitHub deployment governance | Repository rulesets endpoint returns an empty list. Branch-protection inspection returned 403 for the connected GitHub integration; required reviewers and environment branch restrictions could not be independently verified or configured through this connection. | **Not verified / admin action required** |
| Sentry | Code supports Sentry and strips request bodies, cookies, query strings, user data and sensitive headers. No live test event/alert delivery evidence was available. | **Not verified / release blocker** |
| Support | Support-ticket endpoints exist, but no named primary/backup owner, monitored response channel or staffed SLA was evidenced. | **Not verified / release blocker** |
| Privacy | `docs/PRIVACY_NOTICE_DRAFT.md` remains a draft requiring controller identity, contact, retention schedule, vendor review and qualified Nigerian privacy review. | **Not approved / release blocker** |
| Billing | Payment provider integration is not implemented. The plan mutation endpoint previously allowed an owner to select the `family` plan without payment. A follow-up code change now rejects non-pilot plan activation until a verified payment integration is deliberately enabled. | **Code fix proposed; merge and CI required** |

### Required operator actions before production GO

1. Upgrade or reconfigure the Neon project so it supports automated backups/snapshots, sufficient retention, and a protected production branch. Create a fresh post-migration snapshot after the migration plan is approved.
2. Perform a restore drill from a fresh snapshot into an isolated database/branch with compute enabled. Verify the restored Alembic head, representative table counts, household isolation, and staging API readiness. Record RPO/RTO.
3. Configure the Render production and staging health-check path to `/health`; independently probe `/health/live` and `/health` after deployment.
4. Configure GitHub's `production` environment with required reviewers and a `main`-only deployment branch policy using an administrator-capable GitHub account. Confirm settings in the UI/API.
5. Configure Sentry production DSN and alert routing, then trigger a synthetic exception and capture proof that the monitored operator receives the alert. Recheck event scrubbing.
6. Assign named support primary and backup owners, publish a monitored contact channel, and test an end-to-end support ticket.
7. Complete the privacy notice, data retention schedule, processor/transfer review and qualified NDPA/NDPC review before publication.
8. Keep billing in pilot mode. Do not enable paid plan activation until checkout, raw-body signature verification, idempotency, payment reconciliation, subscription lifecycle, refunds and sandbox acceptance are complete.

**Production release decision on 2026-11-25: NO-GO.** The successful staging rollout does not authorize production deployment or migrations.