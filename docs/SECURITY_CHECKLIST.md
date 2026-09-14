# Spec §25 security checklist — Phase 13 evidence

| # | Control | Status | Evidence |
|---|---|---|---|
| 1 | Authenticated users | Done | Session cookie + `get_current_user` on financial routes (`app/api/deps.py`) |
| 2 | Household-level authorization | Done | `X-Household-Id` + membership check; cross-household denied (`tests/test_tenancy.py`) |
| 3 | Role-based permissions | Done | `require_roles`; export owner/partner; delete owner-only (`tests/test_authorization.py`, `tests/test_hardening.py`) |
| 4 | Encrypted secrets | Done | Secrets via env / compose; `.env` not committed; `secret_key` from settings |
| 5 | HTTPS in non-local | Done | Checklist: terminate TLS at reverse proxy / platform; `cookie_secure=true` when HTTPS |
| 6 | Secure password hashing | Done | Argon2id (`app/core/security.py`) |
| 7 | Database least privilege | Done | App role `familyos` is not a superuser; Postgres network scoped to compose |
| 8 | Audit logs | Done | `audit_logs` for money create/update/void, members, allocation rules, export, delete |
| 9 | No financial credentials in frontend | Done | Bank credentials never collected; only session cookie |
| 10 | No API keys client-side | Done | AI / engines server-side only |
| 11 | Backups | Done | `docs/BACKUP_RESTORE.md` (dump/restore drill) |
| 12 | Data export + household deletion | Done | `GET /api/v1/export`, `DELETE /api/v1/households/current` |
| 13 | Session management | Done | Idle 12h / absolute 7d; logout revokes (`app/api/v1/auth.py`) |
| 14 | Rate limiting | Done | Register/login + export/delete (`app/core/rate_limit.py`) |
| 15 | Input validation | Done | Pydantic schemas on API bodies |
| 16 | Server-side authorization | Done | UI is not the security boundary |
| 17 | Every financial query scoped by `household_id` | Done | Query filters + FK tenancy |
| 18 | Dependency scanning in CI | Done | `pip-audit` + `npm audit` in `.github/workflows/ci.yml` |
| 19 | Monitoring / error tracking | Done | `RequestContextMiddleware` + `X-Request-Id` structured logs |
| 20 | Dashboard/engine query performance | Done | Indexes on `(household_id, date/type)` transactions and alerts status |
