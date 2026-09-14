# Phase status

**Current phase:** `14-public-product`  
**Current status:** `complete`  
**Spec version:** 1.1.0

Only the current phase may be implemented. Do not start the next phase until this file says `complete` for the current one.

| Phase | Name | Status | Completed |
|---|---|---|---|
| spec | Product specification | complete | 2026-09-14 |
| 0 | Foundation | complete | 2026-09-14 |
| 1 | Household & Money | complete | 2026-09-14 |
| 2 | Financial Planning | complete | 2026-09-14 |
| 3 | Obligations | complete | 2026-09-14 |
| 4 | Allocation Engine | complete | 2026-09-14 |
| 5 | Wealth | complete | 2026-09-14 |
| 6 | Goals | complete | 2026-09-14 |
| 7 | Business | complete | 2026-09-14 |
| 8 | Analytics | complete | 2026-09-14 |
| 9 | Simulation | complete | 2026-09-14 |
| 10 | Automation | complete | 2026-09-14 |
| 11 | AI | complete | 2026-09-14 |
| 12 | Data Import | complete | 2026-09-14 |
| 13 | Production Hardening | complete | 2026-09-14 |
| 14 | Public Product | complete | 2026-09-14 |

## Evidence log

### spec

- `PRODUCT_SPEC.md` v1.1.0 — IPÌLẸ̀ brand; Tenant #1 ≠ product definition; litmus test; Family Financial Constitution (§41); Family Finance → Wealth → Family Office
- `IMPLEMENTATION_ROADMAP.md` dependency graph and definitions of done
- Cursor rules / `AGENTS.md` enforce spec + configurable rules + one-phase execution

### Phase 0

- `docker compose up` starts Postgres (host 5433), API `:8000`, web `:3000`
- `GET /api/v1/health` → `{"status":"ok"}`
- Register / login / me / logout with HTTP-only `ffos_session` cookie (pytest + live curl)
- Design tokens + `MoneyAmount` on authenticated shell
- CI: backend ruff/pytest, frontend typecheck + money helper tests
- No allocation engine, Safe to Spend, seed household, or money modules yet

### Phase 1

- Households, members (owner/partner/member/viewer), accounts, categories, income sources, transactions
- Balances use Decimal/string amounts; transfers do not change household net cash
- Cross-household access denied; viewer cannot write; member writes only own transactions
- Seed Household is a normal household (Partner A/B, Baby, ₦2m income source)
- Overview shows cash + period income + recent activity only — no Safe to Spend or health
- Backend tests: 16 passed; live seed income ₦2,000,000 updates cash_total

### Phase 2

- Budgets + budget categories; planned vs actual uses spec §9 (`spent = expense + giving − refund`)
- Member-scoped budgets (dependent as a member, no baby table); household Food spend does not hit Baby budget
- Recurring templates with `POST /recurring/{id}/post` advancing `next_date`
- 80% warning and overspend alerts persist; refund can walk an alert back
- Plan screens: `/plan/budget`, `/plan/recurring`; transaction form can assign a member
- Seed: Household essentials ₦670,000 + Baby budget ₦150,000; monthly utilities ₦40,000
- Backend tests: 26 passed (ruff clean); frontend typecheck + money tests ok
- Live: Food ₦200,000 / ₦250,000 → utilization `0.80`, alert `budget_threshold`; recurring posted to 2026-10-14
- No Safe to Spend or health on budget payloads or overview

### Phase 3

- Obligation monthly formulas: ₦450,000 quarterly → ₦150,000; ₦600,000 annual → ₦50,000
- Occurrences generated through a 24-month horizon; create/update is idempotent on `(obligation_id, due_date)`
- Late unpaid occurrences become `missed` and persist a critical alert
- Sinking funds: required monthly, progress, contribution transfer; university provision is `transfer` + system category, not lifestyle spend
- Plan screens: Obligations, Funds; overview 30-day due strip; `GET /api/v1/calendar`
- Seed: Parents' stipend, Sibling University Fees (due 2026-10-15 + University fund), Parents' rent (due 2027-01-15 + Parents Rent Fund)
- Backend tests: 36 passed; frontend typecheck + money tests ok
- Live: required monthly and calendar match; no Safe to Spend or health on overview

### Phase 4

- Allocation engine: percentage, fixed, remainder; leftover kobo absorbed by remainder; no hardcoded tithe/religion
- ₦2,000,000 seed table matches spec §7.3 exactly (Tithe ₦200k through Family surplus ₦200k)
- ₦0 income and income-below-mandatory (₦250,000) take priority order and underfund mandatory rules
- Current STS excludes protected fund/savings balances; seed cash ₦1,760,000 vs STS ₦1,610,000
- Purchase ₦180,000 vs ₦550,000 STS is healthy/affordable (remaining ₦370,000); ₦500,000 warns buffer breach
- Income-recognized posts an allocation run; APIs: `/allocation-rules`, `/allocations/run`, `/allocations/latest`, `/safe-to-spend`, `/purchase-checks`
- Overview shows Income, Allocated, and Safe to Spend as distinct; AllocationBar + purchase-check modal (current/period/forecast)
- Plan screen: `/plan/allocation`; no health or wealth engines
- Backend tests: 52 passed (ruff clean); frontend typecheck + money tests ok

### Phase 5

- Assets, liabilities, investments, investment transactions; emergency via tagged assets/accounts without double-count
- Net worth = assets − liabilities; linked `account_id` excluded from uncategorized cash; credit accounts are not assets
- Transfers do not change net worth; debt payment drops cash and liability together; paid-off excluded from debt
- Period-close snapshots on `GET /api/v1/net-worth`; seed Emergency fund + Family investments
- Overview Wealth strip (net worth / investments / emergency / debt); screens `/wealth`, `/wealth/investments`, `/wealth/debts`
- Layout matches spec §17.12 (Assets | Liabilities, NET WORTH, history); no Goals UI, no health
- Backend tests: 61 passed (ruff clean); frontend typecheck + money tests ok
- Live seed: cash ₦1,760,000 vs STS ₦1,610,000; net worth ₦1,760,000 (cash + university fund); emergency/investments ₦0 until funded
- Live: add vehicle ₦2,500,000 → NW ₦4,260,000; add Car loan ₦500,000 → NW ₦3,760,000; buy ₦10,000 and pay ₦100,000 leave NW unchanged (cash ₦1,500,000, debt ₦400,000)

### Phase 6

- Goals + contributions; required monthly = remaining / months_left (half-up); completed when current ≥ target
- Funding is a transfer from an account into a goal vault; allocation rules may target `destination_type=goal`
- Emergency goals without a linked account count in emergency once; linked vaults are not double-counted
- Seed: Family emergency reserve, Future relocation ₦8,000,000 / ₦2,100,000 / 2027-06-30 (26%, required monthly ₦655,555.56 on 2026-09-14), Long-term wealth
- Screen `/wealth/goals` with GoalProgress; Wealth nav includes Goals; no health or business
- Backend tests: 72 passed (ruff clean); frontend typecheck + money tests ok
- Live: relocation card shows ₦2,100,000 of ₦8,000,000, 26%, deadline 2027-06-30, required monthly ₦655,555.56
- Live contribute ₦10,000 → current ₦2,110,000, required monthly ₦654,444.44

### Phase 7

- Businesses, employees, business transactions; Salon seed with isolated `type=business` account
- Household → business is `capital_contribution`; business → household is `withdrawal`; revenue/expense/payroll stay on the business books
- family_invested = Σ capital; family_withdrawn = Σ withdrawal; return = (withdrawn + equity) − invested
- ₦200,000 into salon does not hit lifestyle budget spent; net worth unchanged; STS drops only household cash
- Business-linked liquid accounts stay out of STS unless `include_in_safe_to_spend` is set
- Screen `/business` answers invested / return; nav Salon; no health or insights
- Backend tests: 78 passed (ruff clean); frontend typecheck + money tests ok
- Live: Salon seed, Stylist employee, invested/return/P/L all ₦0.00 until capital is recorded

### Phase 8

- Health engine: seven weighted components sum to 100; labels Healthy / Watch / Strained / Critical
- `GET /api/v1/health` stays the liveness probe; score lives at `GET /api/v1/financial-health` and `GET /api/v1/financial-health/explain` (raw inputs required)
- Financial snapshots + scores + reports tables; monthly / quarterly / annual / giving payloads persist
- Seed six-month pilot shocks (Apr–Aug constructed, September live freeze) without posting a ₦300k expense onto live balances
- Overview shows FAMILY FINANCIAL HEALTH; Insights and Reports screens; no simulator
- Backend tests: 93 passed (ruff clean); frontend typecheck + money tests ok
- Live: overview 51.18 / 100 Strained; Why 51.18? shows all seven components; April snapshot 88.36 Healthy; Insights six-month series; Reports persist September + Q3 + giving

### Phase 9

- Simulation engine clones household state; income −20%, fee +15%, unexpected ₦300k → month-1 critical cash flow / unfunded obligations / critical emergency
- `POST /api/v1/simulations` persists `simulation_runs`; live account balances unchanged (API guard + tests)
- Screen `/simulate` with status row (cash flow, obligations, emergency, investments, STS, NW delta)
- Backend simulation tests pass; live seed run: income ₦1,600,000, month-1 critical/unfunded/critical, 6 months, balances unchanged

### Phase 10

- Idempotent `scheduler_ticks` by `(household_id, tick_type, period_key)`; duplicate income/daily ticks skip
- Income-recognized chain: allocate → fund sinking lines once → budget alerts → due checks → STS → in-app notifications
- Alerts: budget 80% threshold, overspend, underfunded obligation; `GET /notifications` inbox + mark read
- Screen `/inbox` with Run daily automation; nav under Automation
- Backend automation tests pass (3)

### Phase 11

- Analyst explains verified engine payloads only (health, STS, wealth, budgets, obligations, funds)
- Invented money amounts rejected (`InventingModel` test); template/local model is default (no client API key)
- `POST /api/v1/ai/explain` server-side; Insights "Explain with AI" button
- AI tests pass (4); frontend typecheck ok

### Phase 12

- Import adapters: CSV (`date,amount,external_id` + optional fields) and statement (`date|amount|narrative|reference`)
- Rows normalize into the same `Transaction` model; `import_source` recorded (`csv` / `statement`); dedup by `external_id`
- Partial unique index `(household_id, external_id)`; `import_jobs` metadata; `POST /imports/csv` and `/imports/statement`
- Screen `/money/import`; Money nav Import
- Backend import tests pass (2); frontend typecheck ok
- Live seed: CSV created 1 / duplicate skipped 1; statement created 1; `/money/import` 200

### Phase 13

- Spec §25 checklist evidenced in `docs/SECURITY_CHECKLIST.md`; backup restore drill in `docs/BACKUP_RESTORE.md`
- `audit_logs` for money create/update/void, members, allocation rules, export, household delete
- `GET /api/v1/export` (owner/partner, rate-limited, audited); `DELETE /api/v1/households/current` (owner, soft-delete, audited)
- Request monitoring via `X-Request-Id` + structured access logs; performance indexes on transactions/alerts
- CI dependency scanning: `pip-audit` + `npm audit --omit=dev --audit-level=high`
- Screen `/settings` for export download and household deletion
- Backend tests: 110 passed (incl. hardening 4); frontend typecheck ok; migration `0013_hardening` applied; health returns `X-Request-Id`

### Phase 14

- Public onboarding: register creates household; `/onboarding` after delete; invite token on register; `POST /onboarding/household`
- Invites: `household_invites` + create/list/revoke/accept APIs; Settings Invites UI
- Billing: household `plan` / `billing_status`; Pilot + Family plans; `GET/POST /billing`
- Support tickets + Help/`docs/PUBLIC.md`; multi-household switcher in AppShell
- Soft-deleted seed is never resurrected (`SEED_ON_START` opt-out); no code fork to remove seed
- §35 evidence matrix: `docs/ACCEPTANCE_35.md`
- Backend tests: 116 passed (public product 6); frontend typecheck ok; migration `0014_public_product` applied
- Spec v1.1.0 + brand UX: IPÌLẸ̀ forest/gold tokens, decision-first Home (Safe to Spend hero), simplified nav, global Add, foundation wizard, health hidden until baseline data
