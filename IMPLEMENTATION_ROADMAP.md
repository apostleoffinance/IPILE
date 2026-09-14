# IPÌLẸ̀ — Implementation Roadmap

**Product:** IPÌLẸ̀ (legacy code name: Family Finance OS)  
**Source of truth:** `PRODUCT_SPEC.md` (v1.1.0+)  
**Current phase tracker:** `PHASE_STATUS.md`

Do not implement everything at once. Do not start phase N+1 until phase N is complete per its definition of done. Do not invent a mock mode. Do not shrink this into an MVP that must be rewritten for multiple households. Do not hardcode founding-household concepts into engines.

---

## 1. How to execute

1. Read `PRODUCT_SPEC.md` and this file.
2. Read `PHASE_STATUS.md`. The `current_phase` is the only phase you may implement.
3. Implement only that phase's scope.
4. Prove the phase with its tests and acceptance checks.
5. Mark the phase `complete` in `PHASE_STATUS.md` only when the definition of done is fully met.
6. Stop. Do not "just start" the next phase in the same breath unless the user explicitly asks to continue after completion is recorded.

If a later phase's entity is required as a foreign key, add a **minimal stub table** only (id, household_id, timestamps) and do not build that module's UX or engine.

---

## 2. Dependency graph

```text
                    PRODUCT_SPEC (this program)
                              │
                              ▼
                 Phase 0  Foundation
                    repo, CI, Postgres, design system, auth skeleton
                              │
                              ▼
                 Phase 1  Household & Money
                    users, household, members, accounts,
                    categories, income, transactions
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     Phase 2 Planning   Phase 3 Obligations   (2 and 3 both need Phase 1)
        budgets            bills, sinking
        recurring          funds, occurrences
              │               │
              └───────┬───────┘
                      ▼
           Phase 4  Allocation Engine
              rules, allocation run, Safe to Spend, purchase check
                      │
                      ▼
           Phase 5  Wealth
              savings, investments, assets, liabilities, net worth
                      │
                      ▼
           Phase 6  Goals
                      │
                      ▼
           Phase 7  Business
                      │
                      ▼
           Phase 8  Analytics
              health engine, insights, reports, snapshots
                      │
                      ▼
           Phase 9  Simulation
                      │
                      ▼
           Phase 10 Automation
              scheduler, alerts, notifications
                      │
                      ▼
           Phase 11 AI
              explains verified metrics only
                      │
                      ▼
           Phase 12 Data Import
              CSV / statements / adapter interface
                      │
                      ▼
           Phase 13 Production Hardening
              security review, backups, monitoring, performance
                      │
                      ▼
           Phase 14 Public Product
              onboarding, billing, support, docs
```

**Hard constraints**

- Phase 4 must not start until Phase 2 and Phase 3 are complete. Safe to Spend needs budgets, obligations, and funds.
- Phase 8 health score needs money + planning + obligations + allocation + wealth.
- Phase 9 simulation needs the same engines as production, not a parallel fake model.
- Phase 11 AI is forbidden until engines exist and tests lock their numbers.
- Phase 14 must not introduce a second tenancy model. Tenancy exists from Phase 0/1.

---

## 3. Phases

### Phase 0 — Foundation

**Depends on:** Product spec only.

**Build**

- Repository layout: `backend/`, `frontend/`, `docs/` (optional), root spec files
- Docker Compose: PostgreSQL 16, backend, frontend
- FastAPI app skeleton, settings, logging, health endpoint
- Next.js App Router + TypeScript + Tailwind + design tokens
- Shared money utilities (decimal strings, NGN formatting)
- Auth skeleton: session table, Argon2id password hashing, login/logout/me
- Alembic
- CI: lint, typecheck, backend pytest on engines placeholder, frontend typecheck
- `.gitignore`, env examples without secrets
- Reusable shared UI primitives: EmptyState, LoadingState, ErrorState, Modal
- `MoneyAmount` component

**Do not build:** transactions UI, engines, seed household, dashboards.

**Definition of done**

- `docker compose up` starts Postgres + API + web
- `GET /api/v1/health` returns ok
- User can register, log in, log out; session cookie is HTTP-only
- Design tokens render on a bare authenticated shell
- CI pipeline exists and is green
- No financial engine code beyond a typed money helper
- `PHASE_STATUS.md` updated to complete only after the above

---

### Phase 1 — Household & Money

**Depends on:** Phase 0.

**Build**

- Households, members, roles
- Household scoping on every query
- Accounts and account balances
- Categories
- Income sources and income transactions
- Transactions CRUD (manual)
- Transfers between accounts
- Seed Household attachment for the pilot owner (seed **structure**, not six-month shocks yet)
- Overview shell that lists accounts and recent transactions only (no STS/health yet)
- Money nav: Transactions, Accounts, Income

**Definition of done**

- Owner can create/list accounts and post income/expense/transfer
- Balances update correctly; transfers do not change household net cash incorrectly
- Partner/member/viewer authorization enforced on API tests
- Cross-household access tests fail closed
- Amounts are `DECIMAL` / string decimals, never floats
- Seed household exists as a normal household
- No allocation, STS, or health numbers on the dashboard yet

---

### Phase 2 — Financial Planning

**Depends on:** Phase 1.

**Build**

- Budgets and budget categories
- Planned vs actual
- Recurring transactions
- 80% and overspend alert records (persist even if notification channel is later)
- Budget screens
- Member-scoped budgets (dependent pattern, no "baby" table)

**Definition of done**

- Budget remaining and utilization match spec formulas
- Dependent budget can be created for any member
- Unit tests for zero allocation, overspend, refund reducing spend
- No Safe to Spend yet

---

### Phase 3 — Obligations

**Depends on:** Phase 1. May proceed after or in parallel planning **only if Phase 2 is already complete** (do not interleave unfinished 2 and 3).

**Build**

- Obligations and occurrences (24-month horizon)
- Sinking funds and contributions
- Monthly funding requirement formulas
- Coverage display
- Plan screens: Obligations, Funds
- Calendar data for obligation due dates

**Definition of done**

- ₦450,000 quarterly → ₦150,000/month test
- ₦600,000 annual → ₦50,000/month test
- Occurrence generation is idempotent
- Late occurrences become `missed`
- Fund progress matches contributions
- University provision is not categorized as ordinary lifestyle spend

---

### Phase 4 — Allocation Engine

**Depends on:** Phase 2 and Phase 3.

**Build**

- Allocation rules as data
- Allocation run + lines
- Family surplus as remainder
- Safe-to-spend service (current, period, forecast)
- Purchase check API + UI
- Overview money allocation + Safe to Spend
- Income-recognized → allocate flow

**Definition of done**

- ₦2,000,000 seed allocation table matches spec §7.3 exactly
- ₦0 income and income-below-mandatory tests
- Current STS excludes protected funds
- Purchase ₦180,000 vs ₦550,000 STS affordable; buffer-breach case warns
- Engine has no hardcoded "tithe" or religion
- Dashboard shows Income, Allocated, Safe to Spend as distinct

---

### Phase 5 — Wealth

**Depends on:** Phase 4.

**Build**

- Assets, liabilities, investments, investment transactions
- Emergency fund identification
- Net worth calculation without double-counting
- Net worth over time snapshots (period close hook)
- Wealth screens

**Definition of done**

- Net worth = assets − liabilities with account/asset de-duplication tests
- Transfers do not change net worth
- Debt paid-off case
- Wealth page matches spec layout

---

### Phase 6 — Goals

**Depends on:** Phase 5.

**Build**

- Goals, contributions, required monthly formula
- Funding from accounts/allocations
- Goal progress UI
- Seed relocation goal

**Definition of done**

- Required monthly matches remaining / months_left
- Goal completed status when current ≥ target
- Relocation seed: ₦8,000,000 / ₦2,100,000 / 2027-06-30

---

### Phase 7 — Business

**Depends on:** Phase 6.

**Build**

- Businesses, employees, business transactions
- Capital contribution vs household expense
- Withdrawals
- P/L and family invested / return
- Salon seed

**Definition of done**

- ₦200,000 into salon does not hit lifestyle budget
- Family invested and return formulas tested
- Business account isolated from household STS unless explicitly included

---

### Phase 8 — Analytics

**Depends on:** Phase 7.

**Build**

- Financial health engine + "Why n?"
- Financial snapshots
- Insights (spend, cash flow, net worth trends)
- Monthly / quarterly / annual reports
- Giving report
- Overview health score

**Definition of done**

- Health components sum to total; weights match spec
- Explain endpoint returns raw inputs
- Six-month seed shocks can be snapshotted (seed the six months here or in a script used by this phase)
- Reports persist payload

---

### Phase 9 — Simulation

**Depends on:** Phase 8.

**Build**

- Simulation parameters and runs
- Same engines, cloned state, no mutation of live balances
- Simulator UI

**Definition of done**

- Running a simulation does not change production balances
- Income −20%, fee +15%, unexpected ₦300k produce status bands per spec
- Results stored on `simulation_runs`

---

### Phase 10 — Automation

**Depends on:** Phase 9.

**Build**

- Scheduler (idempotent)
- Income-recognized automation chain
- Due-date and budget threshold alerts
- In-app notifications
- Alert deduplication

**Definition of done**

- Duplicate scheduler ticks do not double-allocate
- Alerts for 80%, overspend, underfunded obligation
- In-app inbox works

---

### Phase 11 — AI

**Depends on:** Phase 10.

**Build**

- Analyst that receives verified engine payloads only
- Natural language over those payloads
- Refusal to emit numbers not in the payload

**Definition of done**

- Tests intercept model output / use a fake model: invented figures are rejected
- AI is behind a server endpoint; no client-side key

---

### Phase 12 — Data Import

**Depends on:** Phase 11 (or Phase 10 if AI is deferred by the user; default is keep order).

**Build**

- Import adapter interface
- CSV import
- Bank statement import path
- Dedup by `external_id`

**Definition of done**

- CSV rows become the same Transaction model as manual entry
- Duplicates do not double-count
- Import source recorded

---

### Phase 13 — Production Hardening

**Depends on:** Phase 12.

**Build**

- Security pass (authz audit, rate limits, backups, HTTPS checklist)
- Monitoring, error tracking
- Performance on dashboard/engine queries
- Data export and household deletion
- Load/backup restore drill documented

**Definition of done**

- Security checklist in spec §25 ticked with evidence
- Export + delete work and are audited
- Backup restore documented

---

### Phase 14 — Public Product

**Depends on:** Phase 13.

**Build**

- Real household onboarding (replace seed by deletion + create, no code fork)
- Invites
- Billing
- Support, public docs
- Multi-household switcher polish

**Definition of done**

- New family can onboard without seed data
- Seed household can be deleted without migrating code
- Billing and support exist
- Spec product-level acceptance criteria §35 all pass

---

## 4. What "complete" means

A phase is complete only if all of the following are true:

1. Scope above is implemented against `PRODUCT_SPEC.md`.
2. Phase tests pass locally and in CI.
3. No files from a later phase's product surface were built "ahead of time" except permitted stubs.
4. `PHASE_STATUS.md` records evidence (tests, key endpoints/screens).
5. The user has not been told the next phase started.

Incomplete work stays in the current phase. Do not mark complete to "keep moving."
