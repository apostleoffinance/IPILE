# IPÌLẸ̀ release acceptance — evidence and certification

**Release candidate:** main branch at the commit under review  
**Acceptance environment:** CI isolated database (SQLite test harness) plus separately identified staging/production smoke environment  
**Rule:** passing CI proves application-level acceptance only. It does not certify production backups, payment settlement, legal compliance, or a live restore.

## 1. Release gates

| Gate | Acceptance evidence | CI coverage | Production evidence |
|---|---|---|---|
| Build and dependency health | Backend lint/tests, dependency audit, frontend typecheck/tests | Required | Deployment state |
| Authentication | Register, login, logout, session expiry, CSRF | Existing backend suite | HTTPS login smoke |
| Tenant isolation | Household A and B cannot read each other's accounts, transactions, exports or support tickets | `test_release_acceptance.py` | Staging test tenants |
| Financial integrity | Balances, transfers, allocations, obligations, budgets, STS, wealth | `test_financial_integrity_acceptance.py` and engine suites | Seeded staging reconciliation |
| Database readiness | DB connectivity and exact migration heads | Health endpoint tests | Production readiness probe |
| Export/deletion | Authorized export, owner-only household deletion, audit trail | Hardening/public product tests | Data-rights exercise |
| Backup/restore | Restore isolated copy, verify schema and household data | Operator drill; never simulated by unit test | Required before GO |
| Monitoring | Request ID, structured logs, alerts and error tracking | Middleware tests | Test alert receipt |
| Privacy/support | Notice, retention, support routing and operator ownership | Documentation and API tests | Owner sign-off |
| Billing | Provider sandbox lifecycle and idempotent webhooks, or paid plans disabled | Existing stub tests only | No paid billing certification yet |

## 2. Multi-household end-to-end scenario

The automated release acceptance test creates two independent household owners.

### Household A
1. Register a new owner and household.
2. Create a bank account and an expense.
3. Create a support ticket.
4. Export the household data and verify its account and transaction are present.
5. Sign out.

### Household B
1. Register a different owner and household.
2. Create a separate bank account and expense.
3. Attempt to read A's account and transaction by identifier; expect not found.
4. Attempt to select A's household using `X-Household-Id`; expect forbidden.
5. Export B's data; verify it contains only B's records.
6. List support tickets; verify A's ticket is absent.
7. Create B's own support ticket and verify only B's ticket is listed.

### Reverse isolation
1. Sign back in as A.
2. Attempt to read B's account and transaction; expect not found.
3. Attempt to select B's household; expect forbidden.
4. Export A's data and verify only A's records.
5. List support tickets and verify only A's ticket is visible.

This is a deterministic integration test using the test database. Run the same scenario with disposable test households against staging before production release. Never use real customer records for release probes.

## 3. Evidence handling

- CI stores JUnit XML for the release acceptance test as a workflow artifact.
- Evidence must include commit SHA, workflow run URL, test result, deployment ID and environment.
- Never attach customer names, email addresses, account identifiers, statement contents, session tokens or raw production exports to CI artifacts.
- Production restore evidence must contain only aggregate counts, checksums, schema/migration heads and synthetic probe outcomes.
- Keep evidence access restricted to release operators.

## 4. Release checklist

- [ ] Backend CI and dependency audit passed.
- [ ] Frontend CI and dependency audit passed.
- [ ] Two-household isolation test passed in CI.
- [ ] Two-household smoke test passed in staging.
- [ ] Financial integrity acceptance suite passed.
- [ ] Production database and migration heads confirmed.
- [ ] Latest backup exists and restore drill passed.
- [ ] Monitoring and error alerts delivered to an on-call owner.
- [ ] Privacy notice and data retention schedule approved.
- [ ] Support route and escalation owner verified.
- [ ] Billing sandbox passed, or all paid entitlements remain disabled.
- [ ] No open critical/high security, privacy, tenancy or financial-integrity defects.
- [ ] Release owner records GO/NO-GO with evidence links.

## 5. Certification record

| Field | Value |
|---|---|
| Release commit | To be recorded by release workflow |
| CI run | To be linked |
| Backend / frontend | To be recorded |
| Tenant isolation | Automated CI test |
| Staging multi-household run | Pending operator execution |
| Backup restore | Pending verified production database access |
| Monitoring alert delivery | Pending configured recipient |
| Privacy approval | Pending designated reviewer |
| Support readiness | Pending named owner and monitored channel |
| Billing readiness | Pilot-only; payment processor not integrated |
| Release decision | **NO-GO until operational blockers are closed** |

## 6. Sign-off

- Engineering: confirms code, CI, migrations and deployment.
- Database operator: confirms backup policy, restore and recovery objectives.
- Security/privacy owner: confirms privacy notice, retention and access controls.
- Support owner: confirms ticket routing and response coverage.
- Product/finance owner: confirms billing mode and customer disclosures.

No individual sign-off substitutes for another control. The release owner must retain the final evidence bundle.
