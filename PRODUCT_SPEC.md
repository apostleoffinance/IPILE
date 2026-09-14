# IPÌLẸ̀ — Product Specification

**Status:** Source of truth  
**Version:** 1.1.0  
**Date:** 2026-09-14  
**Product name:** IPÌLẸ̀  
**Tagline:** The financial foundation for households everywhere.  
**Code / module name (legacy):** Family Finance OS

This document is the complete product definition. Implementation must follow it. Do not treat the first household as an MVP. Architect the production, multi-household product from day one. The first six months are a private production pilot using a seed household. The application must not contain a "mock mode."

**Do not implement everything at once.** Analyze the system, respect the implementation roadmap, and complete one phase before starting the next. See `IMPLEMENTATION_ROADMAP.md` and `PHASE_STATUS.md`.

---

## 0. Foundational principle

> **IPÌLẸ̀ must be built as a configurable financial operating system for households, not as a financial tracker designed around the founders' household.**
>
> The founding household is the first production household and serves as the primary dogfooding environment for the first six months. Its financial structure, obligations, beliefs, categories, income sources, goals and allocation rules must be represented as **configurable data** rather than hard-coded product behavior.
>
> **IPÌLẸ̀ is opinionated about financial discipline, but agnostic about how every household defines its own financial life.**
>
> **If a feature works only for the founding family, it is not an IPÌLẸ̀ feature yet. It is a household configuration.**

### Tenant #1 is not the product definition

```text
                    IPÌLẸ̀
                       │
              Universal Financial
                 Operating System
                       │
       ┌───────────────┼───────────────┐
       │               │               │
    Family A        Family B        Family C
       │               │               │
   Custom rules     Custom rules     Custom rules
```

The founding / seed household is simply:

```text
Household #001 → configuration rows → engines execute those rows
```

Examples that must never become hard-coded product logic: tithe percentage, parents' stipend, university fees, baby expenses, salon business, Nigerian currency defaults beyond household settings, or any religion.

### Product journey

```text
IPÌLẸ̀
  ├── Family Finance     (cash, budget, obligations, STS, health)
  ├── Family Wealth      (savings, investments, assets, debt, goals, net worth)
  └── Family Office      (businesses, properties, insurance, legacy, tax, intergenerational)
```

Phases already shipped implement Family Finance and Family Wealth foundations. Family Office depth grows without rewriting tenancy or engines.

---

## Table of contents

0. Foundational principle
1. Product vision
2. Product principles
3. Personas
4. Core concepts
5. Domain model
6. Financial rules
7. Allocation engine
8. Obligation engine
9. Budget engine
10. Sinking fund engine
11. Safe-to-spend engine
12. Wealth engine
13. Simulation engine
14. Financial health engine
15. AI layer
16. User flows
17. Screen specifications
18. Design system
19. Database schema
20. API contract
21. Backend architecture
22. Frontend architecture
23. Authentication
24. Authorization
25. Security
26. Notifications
27. Reporting
28. Seed data
29. Testing
30. Observability
31. Deployment
32. Data import
33. Future integrations
34. Commercialization
35. Acceptance criteria
36. Purchase check
37. Financial calendar
38. Giving architecture
39. Business accounting
40. Automation engine
41. Family Financial Constitution

---

## 1. Product vision

### Promise

> Know where your money is. Know what it is committed to. Know what you can safely spend. Know whether your family is getting wealthier.

IPÌLẸ̀ is a **household financial operating system**, not an expense tracker.

### One-sentence definition

IPÌLẸ̀ automatically organizes income, obligations, budgets, savings, giving, debt, investments and family goals into one system, giving households a real-time view of their financial health, safe-to-spend money and path toward wealth — using each household's own rules.

### Core loop

```text
INCOME → ALLOCATE → OBLIGATIONS / LIFESTYLE / WEALTH
                 → CASH FLOW → SAFE TO SPEND
                 → NET WORTH → FINANCIAL HEALTH
                 → INSIGHTS → BETTER DECISIONS → repeat
```

### Product manages

```text
INCOME → ALLOCATIONS → OBLIGATIONS → BUDGETS → SPENDING
      → SAVINGS → WEALTH → GOALS → FAMILY DECISIONS
```

The continuous question: **Are we financially healthy?**

### Lifecycle

```text
FULL PRODUCT → PRIVATE HOUSEHOLD DOGFOODING (6 MONTHS)
            → BUG DISCOVERY → FINANCIAL MODEL VALIDATION
            → UX REFINEMENT → BETA HOUSEHOLDS → PUBLIC LAUNCH
```

The six months are product validation, not MVP development. Tenant #1 is the seed / founding household. The software does not fork for that household. Discoveries become product rules only when they generalize beyond one family's configuration.

---

## 2. Product principles

1. **Bank balance ≠ available money.** Safe to Spend is a core differentiator.
2. **Three realities:** Cash (what we have), Commitments (what already has a job), Freedom (what we can safely spend).
3. **Deterministic finance first.** Engines compute numbers. AI only explains verified metrics.
4. **Rules are data.** The engine must not hardcode religion, "baby," tithe, salon, or any household-specific concept. Household configuration does.
5. **Household is the tenant.** Every financial query is scoped by `household_id`.
6. **Production architecture from day one.** Multi-household ready. Seed data, not mock mode.
7. **Modular monolith.** Not microservices.
8. **Every screen answers one decision.**
   - Dashboard: Are we okay?
   - Budget: Are we spending according to plan?
   - Obligations: Are we prepared for what is coming?
   - Safe to Spend: Can we afford this?
   - Wealth: Are we getting richer?
   - Goals: Are we getting closer?
   - Simulator: What happens if?
   - Reports: What happened?
9. **Calm, premium, financial.** Linear + modern banking + household planning. Not a noisy fintech dashboard.
10. **Complete one implementation phase before the next.**
11. **Opinionated discipline, flexible practice.** Mandatory waterfall priority, sinking funds, STS, and health are system opinions. How a household names giving, family shape, categories, and priorities is configuration.
12. **Litmus test.** If a feature works only for the founding family, it is not an IPÌLẸ̀ feature yet — it is a household configuration.
13. **No silent constitution rewrite.** Insights and recommendations may compare plan vs actual; they must not silently change allocation rules, limits, or membership without explicit household action.
14. **Decision-first UX.** Expose complexity to power users without requiring ordinary households to understand the complexity. Prefer Home → Money → Plan → Wealth → Family. Lead with Safe to Spend, attention, and actions — not a module wall.
15. **Human language over engine names.** Prefer “Money plan” over “Allocation engine,” “What needs attention?” over empty admin dashboards, and progressive disclosure for calculations.

---

## 3. Personas

| Persona | Description | Needs |
|---|---|---|
| Owner | Household financial lead. Full control. | Allocation, obligations, health, decisions |
| Partner | Spouse/partner with full financial access | Same visibility, shared decisions, purchase check |
| Member | Adult with limited write access | Own allowance, own transactions, limited views |
| Viewer | Read-only (later: advisor) | Reports and health, no mutation |
| Dependent | Child or other dependent without login | Represented as a member; budgets attach to them |
| Extended support | Parents, siblings funded by the household | Appear as obligation beneficiaries, not necessarily users |

The same system must work for a single person, a couple, a family with children, an extended family, and a multi-generational household.

---

## 4. Core concepts

### 4.1 Household

Root tenant. Owns members, accounts, money, plans, wealth, businesses, and insights.

A household is not assumed to be "husband + wife + children." It may be a single adult, couple, single parent, blended family, multigenerational household, guardians + dependants, adults sharing finances, or dependants living elsewhere funded via obligations. Members, relationships, roles, and permissions are data.

### 4.2 Three financial realities

| Reality | Question | Primary metric |
|---|---|---|
| Cash | How much money do we physically have? | Liquid balances |
| Commitments | How much of that money already has a job? | Allocated + obligated + protected |
| Freedom | How much can we safely spend? | Safe to Spend |

### 4.3 Money movement types

`income` · `expense` · `transfer` · `refund` · `investment` · `debt_payment` · `capital_contribution` · `withdrawal` · `giving`

### 4.4 Allocation

Rules that assign recognized income to destinations (funds, budgets, accounts, obligations, goals, giving) by priority.

### 4.5 Obligation

A future amount that must be paid. May be funded by a sinking fund. Frequency can be weekly, monthly, quarterly, annual, or one-time.

### 4.6 Sinking fund

A reserve that accumulates toward an obligation or goal. Protected from Safe to Spend unless explicitly released.

### 4.7 Budget

A period plan for spending by category, optionally scoped to a member (for example a dependent).

### 4.8 Safe to Spend

Deterministic residual after cash, expected income, commitments, bills, sinking-fund requirements, protected savings, and pending transactions.

Three variants: **Current**, **Period**, **Forecast**.

### 4.9 Financial health

A 0–100 deterministic score with visible component weights. No black-box AI.

### 4.10 Seed household

Synthetic ₦2,000,000/month household used for the private pilot. The application treats it as a normal household.

---

## 5. Domain model

```text
Household
├── Members (users and dependents)
├── Accounts
├── Income Sources
├── Categories
├── Transactions
├── Recurring Transactions
├── Allocation Rules
├── Obligations + Occurrences
├── Sinking Funds + Contributions
├── Budgets + Budget Categories
├── Goals + Contributions
├── Assets
├── Liabilities
├── Investments + Investment Transactions
├── Businesses + Business Transactions + Employees
├── Giving Records
├── Financial Snapshots
├── Financial Scores
├── Alerts + Notifications
├── Simulations + Runs
├── Reports
└── Audit Logs
```

### 5.1 Entity field contracts

All financial entities include `id` (UUID), `household_id` (UUID), `created_at`, `updated_at`. Soft-deletable entities also include `deleted_at`.

#### Household

| Field | Type | Notes |
|---|---|---|
| name | string | Display name |
| slug | string | Unique, URL-safe |
| base_currency | char(3) | Default `NGN` |
| timezone | string | IANA, default `Africa/Lagos` |
| country | string | Default `NG` |
| fiscal_month_start_day | int | Default `1` |
| minimum_buffer_amount | decimal(18,2) | Floor for purchase-check warnings |
| settings | jsonb | Extensible household config |

#### User

| Field | Type | Notes |
|---|---|---|
| email | citext | Unique |
| password_hash | string | Server-side only; never returned |
| display_name | string | |
| avatar_url | string? | |
| status | enum | `active` `invited` `disabled` |
| last_login_at | timestamptz? | |

#### HouseholdMember

| Field | Type | Notes |
|---|---|---|
| user_id | uuid? | Null for dependents without login |
| display_name | string | |
| role | enum | `owner` `partner` `member` `viewer` |
| relationship | enum | `self` `spouse` `child` `parent` `sibling` `other` |
| member_type | enum | `adult` `dependent` |
| date_of_birth | date? | |
| is_financial_contributor | bool | |

#### Account

| Field | Type | Notes |
|---|---|---|
| name | string | |
| type | enum | `bank` `savings` `cash` `wallet` `investment` `business` `credit` `other` |
| currency | char(3) | |
| institution | string? | |
| owner_member_id | uuid? | |
| business_id | uuid? | |
| current_balance | decimal(18,2) | |
| available_balance | decimal(18,2) | |
| is_protected | bool | Excluded from current Safe to Spend |
| include_in_safe_to_spend | bool | |
| include_in_net_worth | bool | Default true |
| status | enum | `active` `closed` `archived` |
| external_id | string? | Future integrations |

#### IncomeSource

| Field | Type | Notes |
|---|---|---|
| member_id | uuid? | |
| name | string | |
| type | enum | `salary` `business` `freelance` `investment` `gift` `other` |
| expected_amount | decimal(18,2) | |
| frequency | enum | `weekly` `biweekly` `monthly` `quarterly` `annual` `irregular` |
| next_expected_date | date? | |
| is_active | bool | |

#### Category

| Field | Type | Notes |
|---|---|---|
| parent_id | uuid? | |
| name | string | |
| kind | enum | `income` `expense` `transfer` `giving` `investment` `debt` `system` |
| is_system | bool | |
| sort_order | int | |

#### Transaction

| Field | Type | Notes |
|---|---|---|
| account_id | uuid | |
| counterparty_account_id | uuid? | Transfers |
| member_id | uuid? | |
| amount | decimal(18,2) | Always ≥ 0. Direction from `type` |
| currency | char(3) | |
| type | enum | See §4.3 |
| category_id | uuid? | |
| date | date | |
| merchant | string? | |
| description | string? | |
| obligation_id | uuid? | |
| budget_id | uuid? | |
| fund_id | uuid? | |
| goal_id | uuid? | |
| business_id | uuid? | |
| giving_record_id | uuid? | |
| status | enum | `pending` `cleared` `reconciled` `voided` |
| external_id | string? | |
| import_source | enum? | `manual` `csv` `statement` `api` `open_banking` |

Amount is always stored positive. Sign is derived:

- Inflow: `income`, `refund`, `withdrawal` (from business to household)
- Outflow: `expense`, `investment`, `debt_payment`, `capital_contribution`, `giving`
- Neutral pair: `transfer` (out of `account_id`, into `counterparty_account_id`)

#### AllocationRule

| Field | Type | Notes |
|---|---|---|
| name | string | e.g. "Tithe" — a label, not a hardcoded concept |
| type | enum | `percentage` `fixed` `remainder` |
| basis | enum | `recognized_income` `remaining` `specific_source` |
| rate | decimal(9,6)? | For percentage |
| amount | decimal(18,2)? | For fixed |
| priority | int | Lower runs first. `0` is first |
| mandatory | bool | |
| destination_type | enum | `fund` `budget` `account` `obligation` `goal` `giving` |
| destination_id | uuid? | |
| income_source_id | uuid? | When basis is `specific_source` |
| is_active | bool | |
| effective_from | date? | |
| effective_to | date? | |

#### Obligation

| Field | Type | Notes |
|---|---|---|
| name | string | |
| amount | decimal(18,2) | Occurrence amount, not monthly unless frequency is monthly |
| currency | char(3) | |
| frequency | enum | `weekly` `monthly` `quarterly` `annual` `one_time` |
| next_due_date | date | |
| priority | enum | `critical` `high` `medium` `low` |
| sinking_fund | bool | |
| auto_allocate | bool | |
| category_id | uuid? | |
| beneficiary_name | string? | |
| beneficiary_member_id | uuid? | |
| fund_id | uuid? | |
| status | enum | `active` `paused` `completed` `cancelled` |

#### ObligationOccurrence

| Field | Type | Notes |
|---|---|---|
| obligation_id | uuid | |
| due_date | date | |
| amount | decimal(18,2) | |
| funded_amount | decimal(18,2) | |
| status | enum | `upcoming` `due` `paid` `missed` `skipped` |
| paid_at | timestamptz? | |
| transaction_id | uuid? | |

#### SinkingFund

| Field | Type | Notes |
|---|---|---|
| name | string | |
| target_amount | decimal(18,2) | |
| current_amount | decimal(18,2) | |
| target_date | date? | |
| obligation_id | uuid? | |
| monthly_contribution | decimal(18,2) | Computed or override |
| account_id | uuid? | |
| is_protected | bool | Default true |
| status | enum | `active` `paused` `completed` `cancelled` |

#### Budget / BudgetCategory

Budget is a period container. Categories hold allocated vs spent.

| Budget field | Type |
|---|---|
| name | string |
| period_type | enum `monthly` `quarterly` `annual` |
| start_date | date |
| end_date | date |
| member_id | uuid? |
| status | enum `draft` `active` `closed` |

| BudgetCategory field | Type |
|---|---|
| category_id | uuid |
| allocated_amount | decimal(18,2) |
| rollover | bool |

Spent is computed from transactions in period, not stored as source of truth.

#### Goal

| Field | Type | Notes |
|---|---|---|
| name | string | |
| type | enum | `education` `housing` `relocation` `purchase` `retirement` `business` `emergency` `other` |
| target_amount | decimal(18,2) | |
| current_amount | decimal(18,2) | |
| deadline | date? | |
| monthly_contribution | decimal(18,2)? | |
| priority | int | |
| funding_source_account_id | uuid? | |
| status | enum | `active` `paused` `completed` `cancelled` |

Required monthly contribution when deadline exists:

```text
remaining = target_amount - current_amount
months_left = max(1, months_between(today, deadline))
required_monthly = remaining / months_left
```

#### Asset / Liability / Investment

| Asset | Liability | Investment |
|---|---|---|
| name, type, current_value, as_of | name, type, current_balance, interest_rate, minimum_payment, due_day | name, type, current_value, cost_basis, institution |
| type: `cash` `savings` `investment` `business` `property` `vehicle` `other` | type: `loan` `credit` `mortgage` `other` | Linked optional `account_id` |
| optional account_id, business_id | optional account_id | |

`include_in_net_worth` defaults true on all three.

#### Business

| Field | Type |
|---|---|
| name | string |
| type | string |
| status | `active` `paused` `closed` |
| account_id | uuid? |

Business transaction types: `revenue` `expense` `capital_contribution` `withdrawal` `payroll`.

Family money into a business is a **capital contribution**, never household lifestyle spend.

#### GivingRecord

| Field | Type | Notes |
|---|---|---|
| kind | string | Household-defined label (e.g. Tithe, Charity). Suggested defaults only — not engine vocabulary |
| beneficiary | string? | |
| amount | decimal(18,2) | |
| date | date | |
| monthly_limit | decimal(18,2)? | On the rule/policy, denormalized for queries |
| annual_limit | decimal(18,2)? | |
| requires_dual_approval | bool? | Optional household boundary (e.g. both partners) |
| allocation_rule_id | uuid? | |
| transaction_id | uuid? | |

A named giving practice (e.g. "Tithe") is an allocation rule and/or giving policy row — never a hard-coded product concept. Other giving can have monthly/annual limits. The product must be able to say "Additional giving: ₦43,000 / ₦50,000 used."

---

## 6. Financial rules

### 6.1 Money arithmetic

- Store money as `DECIMAL(18,2)`. Never floating point.
- Currency of record is household `base_currency` unless an account overrides.
- Phase 0–13 assume single currency per household. Multi-currency conversion is a later extension; schema still stores `currency` on money rows.
- Rounding: half-up to 2 decimal places at each allocation step. Remainder rule absorbs leftover kobo.

### 6.2 Income recognition

An income transaction with status `cleared` or `reconciled` is **recognized income** for its date's fiscal period.

```text
recognized_income(period) = Σ income.amount
  where household_id = H
    and status ∈ {cleared, reconciled}
    and date ∈ period
    and deleted_at is null
```

### 6.3 Period

Default fiscal period is calendar month in household timezone, starting on `fiscal_month_start_day`.

### 6.4 Protected money

Protected if any of:

- account `is_protected = true`
- sinking fund `is_protected = true` and amount is assigned to that fund
- emergency-fund goal/account flagged protected
- allocation destination marked protected

Protected money is excluded from Current Safe to Spend.

### 6.5 No silent budget destruction

Giving beyond configured limits must surface as a warning. It must not silently consume obligation or sinking-fund money.

### 6.6 Household isolation

Every read/write of financial data requires `household_id` from the authenticated membership, never from an untrusted client-supplied household without authorization.

---

## 7. Allocation engine

**Purpose:** Determine where recognized income should go.

### 7.1 Input

- Household
- Period
- Recognized income (actual) and/or expected income (plan)
- Active allocation rules, ordered by `priority` ascending, then `created_at`

### 7.2 Algorithm

```text
pool = basis_amount(rule.basis)
remaining = pool

for rule in active_rules_sorted:
  if rule.type == percentage:
    raw = pool * rule.rate          # if basis is recognized_income
         or remaining * rule.rate   # if basis is remaining
  if rule.type == fixed:
    raw = rule.amount
  if rule.type == remainder:
    raw = remaining

  allocated = min(raw, remaining)   # unless over-allocation policy says otherwise
  allocated = round_half_up(allocated, 2)
  remaining -= allocated
  emit AllocationLine(rule, allocated)

# leftover after remainder rule (or if none exists) is Family Surplus
surplus = remaining
```

Mandatory rules that cannot be fully funded emit an `underfunded_mandatory_allocation` alert. They still take as much as available, in priority order.

### 7.3 Example — ₦2,000,000 recognized income

| Priority | Rule | Type | Result |
|---|---|---|---|
| 0 | Tithe | 10% of recognized income | ₦200,000 |
| 1 | Parents' stipend | fixed ₦100,000 | ₦100,000 |
| 2 | University fund | fixed ₦150,000 | ₦150,000 |
| 3 | Parents' rent fund | fixed ₦50,000 | ₦50,000 |
| 4 | Household essentials | fixed ₦670,000 | ₦670,000 |
| 5 | Emergency fund | fixed ₦150,000 | ₦150,000 |
| 6 | Investments | fixed ₦200,000 | ₦200,000 |
| 7 | Personal allowances | fixed ₦140,000 | ₦140,000 |
| 8 | Additional giving | fixed ₦50,000 | ₦50,000 |
| 9 | Buffer | fixed ₦90,000 | ₦90,000 |
| 10 | Family surplus | remainder | ₦200,000 |

The university ₦150,000 is not lifestyle spending. It is a commitment to a future obligation.

### 7.4 Output

`AllocationResult`:

- `period`
- `recognized_income`
- `lines[]` (`rule_id`, `name`, `amount`, `destination_*`, `mandatory`, `funded`)
- `total_allocated`
- `surplus`
- `unfunded_mandatory[]`

### 7.5 Commercialization constraint

The engine has no concept of Christianity, tithe, or any religion. "Tithe" is a household-configured rule name.

---

## 8. Obligation engine

**Purpose:** Determine what must be funded and when.

### 8.1 Monthly funding requirement

```text
if frequency == monthly:   monthly = amount
if frequency == weekly:    monthly = amount * 52 / 12
if frequency == quarterly: monthly = amount / 3
if frequency == annual:    monthly = amount / 12
if frequency == one_time:
    months_left = max(1, months_between(today, next_due_date))
    monthly = max(0, (amount - already_funded) / months_left)
```

Round half-up to 2 decimals.

### 8.2 Examples

Sibling university fees: ₦450,000 quarterly → ₦150,000/month.

Parents' rent: ₦600,000 annual → ₦50,000/month → Parents Rent Fund.

### 8.3 Coverage

```text
occurrence.coverage = occurrence.funded_amount / occurrence.amount
fund.coverage = current_amount / target_amount   # when linked
```

Statuses:

- `Funded` when coverage ≥ 1
- otherwise `{coverage*100}% funded`

### 8.4 Occurrence generation

On obligation create/update and on the monthly scheduler, generate occurrences through a 24-month horizon (and the next due one-time). Never generate duplicates for the same `obligation_id + due_date`.

### 8.5 Late / missed

If `due_date < today` and status is not `paid` or `skipped`, mark `missed` and emit a critical alert.

---

## 9. Budget engine

**Purpose:** Track planned vs actual spending.

```text
spent(category, period) = Σ expense.amount
  + Σ giving.amount assigned to that category
  − Σ refund.amount assigned to that category
  where status ∈ {pending, cleared, reconciled}
    and date ∈ period

remaining = allocated - spent
utilization = spent / allocated   # 0 if allocated = 0 and spent = 0
                                  # +∞ conceptually if allocated = 0 and spent > 0
```

Alerts:

- ≥ 80% utilization → warning
- `spent > allocated` → overspending alert

Dependent example (not hardcoded as "baby"):

```text
Member (dependent) → Budget ₦150,000
  ├── Food
  ├── Diapers
  ├── Wipes
  ├── Healthcare
  ├── Clothing
  └── Other
```

Another household can create Child 1 / Child 2 / Child 3 without application changes.

---

## 10. Sinking fund engine

**Purpose:** Build reserves for future expenses.

```text
required_monthly = max(obligation_monthly, explicit_monthly_contribution)
shortfall = max(0, required_to_date - current_amount)
on_track = current_amount >= expected_funded_by(today)
progress = current_amount / target_amount
```

`expected_funded_by(today)` assumes even monthly contributions from fund start (or obligation start) to target date.

Contributions create `fund_contributions` and, when money moves, a `transfer` or `expense` transaction linked by `fund_id`.

Protected sinking-fund balances are excluded from Current Safe to Spend.

---

## 11. Safe-to-spend engine

**Purpose:** Compute freedom. This is a first-class service.

### 11.1 Conceptual formula

```text
liquid_cash
+ expected_income
− committed_obligations
− upcoming_bills
− sinking_fund_requirements
− protected_savings
− pending_transactions
= SAFE TO SPEND
```

### 11.2 Definitions

**Liquid cash**  
Sum of `available_balance` for accounts where `include_in_safe_to_spend = true` and type ∈ `{bank, cash, wallet}` and status is `active`. Credit accounts are not liquid cash.

**Expected income**  
For Period and Forecast only: remaining expected income in the horizon that is not yet recognized.

**Committed obligations**  
Remaining unfunded amount of active obligation occurrences due inside the horizon.

**Upcoming bills**  
Recurring expense transactions / budgeted bills due inside the horizon that are not already counted as obligations.

**Sinking-fund requirements**  
Unfunded required contributions inside the horizon for active protected funds.

**Protected savings**  
Balances flagged protected (emergency, wealth accounts marked protected).

**Pending transactions**  
Outbound `pending` amounts not already subtracted from `available_balance`.

### 11.3 Three outputs

#### Current Safe to Spend

What can be spent now. Horizon = today. Expected income = 0.

```text
current_sts = liquid_spendable
            − unfunded_obligations_due_today_or_overdue
            − pending_outbound
            − protected_amounts_held_in_spendable_accounts
```

#### Period Safe to Spend

What can be spent for the rest of the fiscal period.

```text
period_sts = current_sts
           + remaining_expected_income_this_period
           − remaining_mandatory_allocations
           − remaining_unfunded_occurrences_this_period
           − remaining_protected_fund_contributions_this_period
```

#### Forecast Safe to Spend

What can be spent while still meeting commitments across the forecast horizon (default 90 days).

```text
forecast_sts = project_liquid(horizon)
             − project_unfunded_commitments(horizon)
             − minimum_buffer_amount
```

If `forecast_sts < 0`, the engine still returns the negative number and a `critical` liquidity risk.

### 11.4 Guardrails

- Never use floating point.
- Never include protected emergency or sinking-fund money in current STS unless the household explicitly unprotects it.
- Surplus is spendable only after mandatory allocations for the period are funded.

---

## 12. Wealth engine

**Purpose:** Assets, liabilities, net worth.

```text
total_assets      = Σ assets.current_value where include_in_net_worth
                  + Σ spendable and savings account balances not already counted as assets
total_liabilities = Σ liabilities.current_balance where include_in_net_worth
net_worth         = total_assets − total_liabilities
```

Do not double-count. If an account is linked to an asset, use the asset value or the account balance according to `asset.current_value` as source of truth, and exclude the account from the "uncategorized cash" add-on.

Emergency fund = sum of accounts/funds/goals tagged emergency.

Investments = sum of investment current values.

Debt = total liabilities.

Snapshot net worth at period close for the net-worth-over-time chart.

---

## 13. Simulation engine

**Purpose:** Hypothetical scenarios. Major module, not an afterthought.

### 13.1 Inputs (parameters JSON)

| Parameter | Type | Meaning |
|---|---|---|
| monthly_income | decimal | Override expected income |
| income_change_rate | decimal | e.g. `-0.20` |
| expense_category_deltas | map | e.g. dependent budget `+0.20` |
| obligation_deltas | map | e.g. school fees `+0.15` |
| investment_override | decimal? | |
| unexpected_expense | decimal? | One-time shock |
| horizon_months | int | Default 12 |

The engine copies the household's current state and applies deltas. It does not mutate production balances.

### 13.2 Outputs

For each projected month and a summary:

| Metric | Status bands |
|---|---|
| Cash flow | healthy / warning / critical |
| Obligations | funded / at risk / unfunded |
| Emergency fund | healthy / warning / critical |
| Investments | on plan / reduced / paused |
| Safe to Spend | healthy / warning / critical |
| Net worth | projected delta |

Status thresholds (defaults, household-overridable later):

- Cash flow warning if period surplus < 5% of income; critical if negative.
- Obligations warning if any occurrence coverage < 1.00 before due; critical if < 0.80 at 14 days.
- Emergency warning if < 1 month of essential expenses; critical if < 0.5 month.
- STS critical if forecast STS < minimum buffer; warning if < 2× buffer.

### 13.3 Private pilot scenarios (seed)

| Month | Shock |
|---|---|
| 1 | Normal ₦2,000,000 income |
| 2 | University fees due (₦450,000) |
| 3 | Income falls to ₦1,500,000 |
| 4 | Income increases to ₦2,800,000 |
| 5 | Parents' rent due (₦600,000) |
| 6 | Unexpected ₦300,000 family expense |

The product must survive all six without corrupting balances or hiding underfunding.

---

## 14. Financial health engine

Deterministic. Visible math. No black-box AI.

| Component | Weight | Score 0–weight |
|---|---|---|
| Cash-flow health | 20 | Surplus ratio vs income |
| Obligation coverage | 20 | Funded / due in next 90 days |
| Emergency readiness | 15 | Months of essentials covered |
| Debt health | 15 | Debt-to-asset and payment performance |
| Savings discipline | 10 | Actual vs planned savings |
| Investment discipline | 10 | Actual vs planned investment |
| Budget discipline | 10 | Categories within plan |
| **Total** | **100** | |

### 14.1 Component formulas

**Cash-flow health (20)**

```text
surplus_ratio = period_surplus / recognized_income
score = 0 if income = 0 and surplus ≤ 0
score = 10 if income = 0 and surplus > 0
else clamp(surplus_ratio / 0.10, 0, 1) * 20
```

10% surplus → full 20.

**Obligation coverage (20)**

```text
coverage = funded_due_90 / due_90
score = coverage * 20
```

If nothing due in 90 days, score 20.

**Emergency readiness (15)**

```text
months = emergency_balance / monthly_essentials
score = clamp(months / 3, 0, 1) * 15
```

3 months essentials → full 15.

**Debt health (15)**

```text
if total_liabilities = 0: 15
else:
  dta = total_liabilities / max(total_assets, 1)
  leverage = clamp(1 - dta / 0.40, 0, 1)   # 40% debt-to-asset → 0
  missed = 0 if any missed debt payment in 90 days else 1
  score = (0.7 * leverage + 0.3 * missed) * 15
```

**Savings discipline (10)**

```text
planned = allocated_to_savings_and_emergency_this_period
actual = contributions_this_period
score = 10 if planned = 0 and actual ≥ 0
else clamp(actual / planned, 0, 1) * 10
```

**Investment discipline (10)**

Same pattern against planned investment allocation.

**Budget discipline (10)**

```text
categories_ok = count(spent ≤ allocated) / count(budget_categories)
overspend_severity = min(1, total_overspend / total_allocated)
score = (0.7 * categories_ok + 0.3 * (1 - overspend_severity)) * 10
```

### 14.2 Labels

| Score | Label |
|---|---|
| 80–100 | Healthy |
| 60–79 | Watch |
| 40–59 | Strained |
| 0–39 | Critical |

"Why {n}?" returns every component, its weight, its raw inputs, and its points. Required.

---

## 15. AI layer

AI comes **after** the financial engine. Not before Phase 11.

```text
FINANCIAL DATA → DETERMINISTIC ENGINE → VERIFIED METRICS → AI ANALYST
              → natural-language explanation
```

AI may explain verified metrics. AI must not invent financial figures. If a number is shown, it must come from an engine response already persisted or computed in that request.

Examples of allowed output:

- "Your household spent 18% more on food this month than its three-month average."
- "Your university fund is on track, but the next contribution should be completed before October 15."

---

## 16. User flows

### 16.1 Sign in / first household

1. Authenticate.
2. If user has no membership, create household (public product) or join invite.
3. Configure the household's Family Financial Constitution (allocation waterfall, buffer, key obligations) — or accept defaults and refine later.
4. Pilot: seed household already exists as Tenant #1 configuration; user is attached as Owner.

### 16.2 Income arrives

1. Record income (manual, import, or later integration).
2. Recognize income.
3. Run allocation engine.
4. Fund sinking funds / goals according to rules.
5. Update budgets, Safe to Spend, health.
6. Emit alerts.

### 16.3 Record spend

1. Choose account, amount, category, optional member.
2. Optional: run Purchase Check before commit.
3. Persist transaction.
4. Recalculate budget utilization, STS, health.

### 16.4 Purchase check

1. Enter amount (and optional category).
2. Engine returns affordability vs Current / Period STS, obligation impact, buffer impact.
3. User confirms or cancels.

### 16.5 Obligation due

1. Calendar and Overview show upcoming occurrence.
2. If fund coverage < 1, warning/critical by threshold.
3. Payment records a transaction, marks occurrence `paid`, decrements fund.

### 16.6 Period close

1. Freeze snapshot (income, expenses, allocations, STS, net worth, health).
2. Generate monthly report.
3. Roll budgets if configured.
4. Generate next occurrences.

---

## 17. Screen specifications

Visual identity: calm, premium, financial. Warm/neutral light theme; deep charcoal dark mode. Large legible numbers. Minimal cards. Semantic status only.

### 17.1 Navigation

Desktop sidebar:

```text
FAMILY FINANCE
OVERVIEW
MONEY
  Transactions
  Accounts
  Income
PLAN
  Budget
  Obligations
  Funds
FAMILY
  Members
  Giving
WEALTH
  Net Worth
  Investments
  Goals
  Debts
BUSINESS
INSIGHTS
SIMULATOR
REPORTS
SETTINGS
```

Mobile bottom nav: `Home | Money | Plan | Wealth | More`

### 17.2 Overview (command centre)

Decision: **Are we okay?**

```text
┌─────────────────────────────────────────────────────────────┐
│ Good {morning|afternoon|evening}, {Household}   {Month Year}│
│                                                             │
│ FAMILY FINANCIAL HEALTH                                     │
│                      {score} / 100                          │
│                      {Healthy|Watch|Strained|Critical}      │
├─────────────────────────────────────────────────────────────┤
│ {Income}            {Allocated}           {Safe to Spend}   │
│ Income              Allocated             Safe to Spend     │
├─────────────────────────────────────────────────────────────┤
│ MONEY ALLOCATION          (AllocationBar list)              │
├─────────────────────────────────────────────────────────────┤
│ UPCOMING OBLIGATIONS      (ObligationCard list)             │
├─────────────────────────────────────────────────────────────┤
│ WEALTH                                                  →   │
│ Net worth    {n}     Investments {n}                        │
│ Emergency    {n}     Debt        {n}                        │
└─────────────────────────────────────────────────────────────┘
```

Health is tappable → "Why {n}?" breakdown. Safe to Spend is tappable → three variants + purchase check.

### 17.3 Money — Transactions

Decision: **What moved?**

Table: date, description/merchant, account, member, category, type, amount, status. Filters: date range, account, type, category, member, status, search. Form: all transaction fields in §5. Empty / loading / error states required.

### 17.4 Money — Accounts

Decision: **Where does cash live?**

List of accounts with type, institution, owner, balance, protected flag. Detail: balances over time, recent transactions.

### 17.5 Money — Income

Decision: **What is coming in?**

Income sources with expected vs recognized this period. Record income action.

### 17.6 Money — Cash flow

Decision: **Is money flowing the right way this period?**

Inflow / outflow / net, plus upcoming 30-day obligation strip.

### 17.7 Plan — Budget

Decision: **Are we spending according to plan?**

Period selector. Category rows with BudgetProgress. Member-scoped budgets as sections.

### 17.8 Plan — Obligations

Decision: **Are we prepared for what is coming?**

Cards: name, amount, due, coverage, priority. Detail: occurrences, linked fund, payment action.

### 17.9 Plan — Funds

Decision: **Are reserves building on time?**

FundProgress for each sinking fund. Contribution action.

### 17.10 Family — Members

Household members, roles, dependents. Create dependent → optional budget template.

### 17.11 Family — Giving

```text
GIVING (household-configured kinds)
├── Example: Tithe / Church / Family assistance
├── Example: Charity / Gifts / Spontaneous
└── Custom kinds the household defines
```

Show allocation-rule giving funded vs rule. Show additional giving used vs monthly/annual limits. Dual-approval boundaries are household configuration when enabled.

### 17.12 Wealth — Net Worth

Decision: **Are we getting richer?**

```text
Assets                Liabilities
Cash                  Loans
Savings               Credit
Investments           Other
Business
Property
Total Assets          Total Debt
               NET WORTH
          Net worth over time
```

### 17.13 Wealth — Investments / Goals / Debts

Goal progress: target, current, %, deadline, required monthly. Example goal: Switzerland Relocation, ₦8,000,000 target, ₦2,100,000 current, 26%, deadline June 2027.

### 17.14 Business

Revenue, expenses, employees, capital, withdrawals, P/L. Distinct from household spend. Answer: "How much has the family invested?" and "Has the business generated a return?"

```text
family_invested = Σ capital_contribution
family_withdrawn = Σ withdrawal
return = (family_withdrawn + current_business_equity) − family_invested
```

### 17.15 Insights

Spending analysis, cash-flow trends, net-worth trends, health history, behaviour (top categories, overspend, giving vs limit).

### 17.16 Simulator

Decision: **What happens if?**

Controls for income, income change, category deltas, obligation deltas, investment, unexpected expense. Result: status row for cash-flow, obligations, emergency, investments, STS, net worth.

### 17.17 Reports

Monthly, quarterly, annual, net-worth statement, cash-flow statement, giving report. Export later (Phase 13/14).

### 17.18 Settings

Household, members, categories, rules, currency, notifications, privacy, security, data export, account deletion.

### 17.19 Financial calendar

Month grid of obligation occurrences, recurring bills, scheduled allocations, monthly review. Header: "Financial obligations due in next 30 days."

### 17.20 Purchase check (modal / route)

See §36.

---

## 18. Design system

### 18.1 Principles

- Warm/neutral light. Deep charcoal dark.
- Restrained green/teal accent. Not generic fintech gradients.
- Inter or Geist-style sans. Tabular numbers.
- Minimal cards. Clean charts. Semantic status only: `healthy` `warning` `critical` `neutral`.
- Do not turn every number into a colourful card.

### 18.2 Tokens (initial)

```text
color.bg.canvas          light #F7F4EF    dark #161616
color.bg.surface         light #FFFFFF    dark #1E1E1E
color.bg.subtle          light #EFEBE4    dark #262626
color.text.primary       light #1A1A1A    dark #F5F5F5
color.text.secondary     light #5C5C5C    dark #B3B3B3
color.accent.primary     #0F6E56
color.status.healthy     #0F6E56
color.status.warning     #B45309
color.status.critical    #B42318
color.status.neutral     #6B6B6B
color.border             light #E4DFD6    dark #2C2C2C
radius.md                12
space.unit               8
font.sans                Geist / Inter
font.number              tabular-nums
```

### 18.3 Required reusable components

```text
components/
├── financial/
│   ├── MoneyAmount
│   ├── SafeToSpend
│   ├── FinancialHealth
│   ├── AllocationBar
│   ├── BudgetProgress
│   ├── ObligationCard
│   ├── FundProgress
│   ├── GoalProgress
│   ├── NetWorthChart
│   └── CashFlowChart
├── transactions/
│   ├── TransactionTable
│   ├── TransactionForm
│   ├── TransactionFilters
│   └── CategorySelector
├── dashboard/
│   ├── Overview
│   ├── MoneySummary
│   ├── UpcomingObligations
│   └── WealthSummary
└── shared/
    ├── Modal
    ├── Drawer
    ├── EmptyState
    ├── LoadingState
    ├── ErrorState
    └── ConfirmationDialog
```

No page-only one-off money formatting. All money goes through `MoneyAmount`.

---

## 19. Database schema

PostgreSQL. UUID primary keys. `household_id` on every financial table. Indexes on `(household_id, ...)` for all tenant queries. Foreign keys. Check constraints for non-negative amounts where the model requires them.

### 19.1 Tables

```text
households
users
household_members
household_invites

accounts
account_balances

income_sources

categories

transactions
recurring_transactions

allocation_rules
allocation_runs
allocation_lines

budgets
budget_categories

obligations
obligation_occurrences

sinking_funds
fund_contributions

goals
goal_contributions

assets
liabilities

investments
investment_transactions

businesses
business_employees
business_transactions

giving_policies
giving_records

financial_snapshots
financial_scores

alerts
notifications

simulations
simulation_runs

reports
audit_logs
sessions
```

### 19.2 Relationships (critical)

- `households 1—* household_members *—0..1 users`
- `households 1—* accounts 1—* transactions`
- `transactions` optionally belong to obligation, budget, fund, goal, business, giving_record
- `obligations 1—* obligation_occurrences`
- `obligations 0..1—0..1 sinking_funds`
- `allocation_runs 1—* allocation_lines`
- `businesses 1—* business_transactions`
- Every financial child row copies `household_id` (denormalized) and must match the parent's household (enforced in application and, where practical, composite FKs)

### 19.3 Constraints

- `transactions.amount >= 0`
- Transfer requires `counterparty_account_id`
- Percentage rules require `rate` between 0 and 1 inclusive
- Exactly one `owner` member per household
- Unique `(household_id, slug)`-style names where specified (household slug globally unique)

---

## 20. API contract

Base path: `/api/v1`  
Auth: session cookie (HTTP-only, Secure, SameSite=Lax) + CSRF for cookie-auth mutations.  
All financial responses are household-scoped from the session, not from a client-supplied household id unless the user belongs to multiple households and selects one (header `X-Household-Id` must match a membership).

Money JSON: string decimal `"2000000.00"` or integer kobo plus currency. **Decision: string decimal + ISO currency** to avoid JS float bugs.

Error shape:

```json
{
  "error": {
    "code": "obligation_underfunded",
    "message": "University fees are 82% funded.",
    "details": {}
  }
}
```

### 20.1 Endpoints

#### Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/password/change
```

#### Households & members

```text
GET    /api/v1/households
POST   /api/v1/households
GET    /api/v1/households/current
PATCH  /api/v1/households/current
GET    /api/v1/members
POST   /api/v1/members
PATCH  /api/v1/members/{id}
DELETE /api/v1/members/{id}
```

#### Money

```text
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PATCH  /api/v1/accounts/{id}

GET    /api/v1/transactions
POST   /api/v1/transactions
GET    /api/v1/transactions/{id}
PATCH  /api/v1/transactions/{id}
POST   /api/v1/transactions/{id}/void

GET    /api/v1/income
POST   /api/v1/income
GET    /api/v1/income/sources
POST   /api/v1/income/sources

GET    /api/v1/cash-flow
GET    /api/v1/recurring
POST   /api/v1/recurring
```

#### Planning

```text
GET    /api/v1/budget
POST   /api/v1/budget
GET    /api/v1/budget/{id}
PATCH  /api/v1/budget/{id}

GET    /api/v1/categories
POST   /api/v1/categories

GET    /api/v1/obligations
POST   /api/v1/obligations
GET    /api/v1/obligations/{id}
PATCH  /api/v1/obligations/{id}

GET    /api/v1/funds
POST   /api/v1/funds
POST   /api/v1/funds/{id}/contributions

GET    /api/v1/allocation-rules
POST   /api/v1/allocation-rules
POST   /api/v1/allocations/run
GET    /api/v1/allocations/latest
```

#### Safe to spend & purchase check

```text
GET  /api/v1/safe-to-spend
POST /api/v1/purchase-checks
```

#### Family / giving

```text
GET    /api/v1/giving
POST   /api/v1/giving
GET    /api/v1/giving/summary
```

#### Wealth

```text
GET    /api/v1/net-worth
GET    /api/v1/assets
POST   /api/v1/assets
GET    /api/v1/liabilities
POST   /api/v1/liabilities
GET    /api/v1/investments
POST   /api/v1/investments
GET    /api/v1/goals
POST   /api/v1/goals
POST   /api/v1/goals/{id}/contributions
```

#### Business

```text
GET    /api/v1/businesses
POST   /api/v1/businesses
GET    /api/v1/businesses/{id}
GET    /api/v1/businesses/{id}/pnl
POST   /api/v1/businesses/{id}/transactions
```

#### Insights, simulation, reports

```text
GET    /api/v1/dashboard
GET    /api/v1/health
GET    /api/v1/insights
POST   /api/v1/simulations
GET    /api/v1/simulations/{id}
GET    /api/v1/reports/monthly
GET    /api/v1/reports/quarterly
GET    /api/v1/reports/annual
GET    /api/v1/calendar
```

#### Settings / data rights

```text
GET    /api/v1/alerts
POST   /api/v1/alerts/{id}/read
GET    /api/v1/export
DELETE /api/v1/households/current
```

### 20.2 Representative payloads

`GET /api/v1/safe-to-spend`

```json
{
  "currency": "NGN",
  "current": "550000.00",
  "period": "550000.00",
  "forecast": "410000.00",
  "horizon_days": 90,
  "components": {
    "liquid_cash": "1400000.00",
    "expected_income": "0.00",
    "committed_obligations": "850000.00",
    "upcoming_bills": "0.00",
    "sinking_fund_requirements": "0.00",
    "protected_savings": "0.00",
    "pending_transactions": "0.00"
  }
}
```

`POST /api/v1/purchase-checks`

```json
{
  "amount": "180000.00",
  "category_id": null
}
```

```json
{
  "amount": "180000.00",
  "affordable": true,
  "severity": "healthy",
  "remaining_current_sts": "370000.00",
  "obligations_affected": [],
  "buffer_breached": false,
  "recommended_action": "proceed"
}
```

---

## 21. Backend architecture

Stack: **FastAPI** · Python 3.12+ · SQLAlchemy 2 · Alembic · PostgreSQL 16 · Pydantic v2.

```text
backend/
├── app/
│   ├── api/                 # routers, deps
│   ├── core/                # config, security, logging
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── modules/
│   │   ├── households/
│   │   ├── accounts/
│   │   ├── transactions/
│   │   ├── income/
│   │   ├── budgets/
│   │   ├── obligations/
│   │   ├── funds/
│   │   ├── goals/
│   │   ├── wealth/
│   │   ├── businesses/
│   │   ├── giving/
│   │   ├── allocations/
│   │   ├── safe_to_spend/
│   │   ├── health/
│   │   ├── simulations/
│   │   ├── reports/
│   │   └── notifications/
│   ├── engines/             # deterministic financial engines
│   └── main.py
├── migrations/
├── tests/
└── scripts/
```

**Modular monolith.** Engines are pure functions/services over typed inputs. They do not query the HTTP layer. Repositories are the only DB access.

---

## 22. Frontend architecture

Stack: **Next.js** (App Router) · TypeScript · Tailwind · the design tokens in §18.

```text
frontend/
├── app/                     # routes matching navigation
├── components/              # financial / transactions / dashboard / shared
├── lib/                     # api client, money, dates
├── styles/
└── tests/
```

Rules:

- Server components for read shells; client components for interactive money forms.
- All money rendering via `MoneyAmount`.
- Household context from session; never persist secrets in `localStorage`.
- Route groups match the sidebar modules.

---

## 23. Authentication

- Email + password at Phase 0/1. Password hashing: Argon2id.
- HTTP-only session cookies. Server-side session table. Idle timeout 12 hours. Absolute timeout 7 days.
- Optional later: passkeys / OIDC.
- No financial credentials in the frontend.
- No API keys in client bundles.
- Register/login rate limited.
- Password minimum 12 characters.
- Logout revokes session.

---

## 24. Authorization

| Role | Read financials | Write money | Rules & settings | Members | Export / delete |
|---|---|---|---|---|---|
| Owner | yes | yes | yes | yes | yes |
| Partner | yes | yes | yes | invite only | export |
| Member | limited (own / granted) | own transactions | no | no | no |
| Viewer | yes | no | no | no | no |

Later: Financial Advisor = permissioned viewer.

Authorization is enforced server-side on every endpoint. UI hiding is not security.

---

## 25. Security

Designed from day one, including the private pilot.

- Authenticated users
- Household-level authorization
- Role-based permissions
- Encrypted secrets (env / secret manager, never committed)
- HTTPS in all non-local environments
- Secure password hashing (Argon2id)
- Database access controls and least-privilege roles
- Audit logs for create/update/void on money, rules, members, exports
- No financial credentials in frontend
- No API keys client-side
- Backups (Phase 13 automated; Phase 0 documents the plan)
- Data export and account/household deletion
- Session management
- Rate limiting
- Input validation (Pydantic)
- Server-side authorization
- Every financial query scoped by `household_id`
- Dependency scanning in CI

---

## 26. Notifications

### Channels

Phase 10: in-app. Later: email, push. WhatsApp/SMS only if commercially viable.

### Examples

- University fund is 82% funded. (warning)
- Food budget exceeded by ₦32,000. (critical)
- Emergency fund reached one month of expenses. (healthy)
- Projected cash may fall below minimum reserve in 18 days. (critical)

### Triggers (automation)

See §40. Alerts persist even if a channel is disabled.

---

## 27. Reporting

### Monthly family report

```text
FAMILY FINANCIAL REPORT
{Month Year}

Income                 {n}
Expenses               {n}
Savings                {n}
Investments            {n}
Giving                 {n}
Debt reduction         {n}
Surplus                {n}

Net worth change       {n}
Top overspend          {category}
Best improvement       {metric}
Upcoming risk          {obligation}
Financial health       {score}/100
```

Also: quarterly, annual, net-worth statement, cash-flow statement, giving report.

Reports are generated from snapshots + live engines, then stored in `reports.payload`.

---

## 28. Seed data

Create **Seed Household**. The app does not know ₦2m is synthetic.

### Household

- Name: `Seed Household`
- Currency: `NGN`
- Timezone: `Africa/Lagos`
- Minimum buffer: ₦90,000

### Members

| Display name | Role | Type | Relationship |
|---|---|---|---|
| Partner A | owner | adult | self |
| Partner B | partner | adult | spouse |
| Baby | member | dependent | child |

### Income

- Source: Household income, ₦2,000,000, monthly.

### Allocation (monthly, ₦2,000,000)

| Name | Amount |
|---|---|
| Tithe | ₦200,000 (10%) |
| Parents' stipend | ₦100,000 |
| University fund | ₦150,000 |
| Parents' rent fund | ₦50,000 |
| Household essentials | ₦670,000 |
| Emergency fund | ₦150,000 |
| Investments | ₦200,000 |
| Personal allowances | ₦140,000 |
| Additional giving | ₦50,000 |
| Buffer | ₦90,000 |
| Family surplus | ₦200,000 remainder |

### Obligations

| Name | Amount | Frequency | Sinking fund |
|---|---|---|---|
| Tithe | rule-driven | monthly | no (allocation) |
| Parents' stipend | ₦100,000 | monthly | optional |
| Sibling University Fees | ₦450,000 | quarterly | yes, auto-allocate |
| Parents' rent | ₦600,000 | annual | yes, auto-allocate |

University next due in seed: **2026-10-15**.  
Parents' rent next due aligned so Month 5 of the six-month series pays it.

### Household budgets (from essentials + personal + giving + dependent)

Categories include Food, Transport, Utilities, Personal, Giving, and a dependent budget of ₦150,000 (Food, Diapers, Wipes, Healthcare, Clothing, Other). Exact category splits are defined in `backend/scripts/seed.py` and must sum consistently with allocations.

### Wealth

- Emergency fund account/fund
- Investment account
- Goal: Family emergency reserve
- Goal: Future relocation — target ₦8,000,000, current ₦2,100,000, deadline 2027-06-30
- Goal: Long-term wealth

### Business

- Salon. Family capital contributions are `capital_contribution`, not household expense.

### Six-month series

Seed at least six fiscal periods as specified in §13.3 so engines can be tested against real shocks.

---

## 29. Testing

Financial software cannot rely on visual testing alone.

### Unit

Tithe/percentage allocation, fixed allocation, remainder, budget remaining, sinking-fund monthly, obligation monthly, current/period/forecast STS, net worth (no double-count), debt health, forecast math, health components.

### Integration

Income → allocation → transactions → balances → STS → health.

### Scenario

₦2m income → 10% tithe → obligations → budget → surplus = ₦200,000.

### Edge cases (must have tests)

- ₦0 income
- Negative input rejected
- Income below mandatory obligations
- Income above expectations
- Duplicate transaction (idempotency key / external_id)
- Refunded transaction
- Deleted/voided transaction restores computed balances
- Late obligation
- Missed fund contribution
- Debt paid off
- Goal completed
- Transfer between household accounts does not change net worth
- Capital contribution does not reduce lifestyle budget
- Cross-household access denied

### Frontend

Component tests for MoneyAmount, health label bands, purchase-check severity. Playwright smoke after Phase 1.

---

## 30. Observability

- Structured JSON logs. No secrets, no full card/account numbers.
- Request id on every API response.
- Metrics: request latency, 4xx/5xx, allocation run duration, scheduler success.
- Error tracking ready (Sentry or equivalent) from Phase 13; stub interface earlier.
- Audit log is not a substitute for application logs.

---

## 31. Deployment

- Local: Docker Compose with `postgres`, `backend`, `frontend`.
- CI: lint, typecheck, unit + engine tests, migration check.
- Staging and production: HTTPS, managed Postgres, migrations on deploy, backups.
- No production deploy until Phase 13 hardening acceptance is met.

---

## 32. Data import

Phase-independent architecture. All sources produce the same `Transaction`.

```text
Manual entry → Transaction
CSV import → Transaction
Bank statement import → Transaction
API integrations → Transaction
Open banking → Transaction
```

Do not build the product around a spreadsheet mindset. Import modules normalize into the transaction schema.

---

## 33. Future integrations

- Nigerian (and later other) bank APIs / open banking
- Statement PDF/CSV parsers
- Email/push providers
- WhatsApp/SMS if commercially viable
- Advisor/read-only invites
- Multi-currency FX service

Integrations are adapters. They must not leak into engine math.

---

## 34. Commercialization

- Product brand: **IPÌLẸ̀** — financial foundation for households everywhere
- Journey: Family Finance → Family Wealth → Family Office
- Multi-household tenancy from day one
- Roles including future advisor
- Allocation rules as data (no religious hardcoding)
- Dependents as members + budgets (no "baby" schema)
- Billing, onboarding, support, and public docs are Phase 14
- Intellectual property is the deterministic Household Financial Intelligence Engine, not the dashboard chrome
- Founding household = Tenant #1 dogfood; never a product fork

---

## 35. Acceptance criteria

A phase is complete only when its criteria in `IMPLEMENTATION_ROADMAP.md` are met, tests pass, and the product spec is not violated.

### Product-level (full system)

1. A household can record income and see allocation, obligations, budgets, STS, and health update.
2. Bank balance and Safe to Spend are different numbers when commitments exist.
3. ₦2,000,000 seed month allocates exactly to the table in §7.3.
4. Quarterly ₦450,000 obligation requires ₦150,000/month.
5. Annual ₦600,000 obligation requires ₦50,000/month.
6. Purchase of ₦180,000 against ₦550,000 STS is affordable; ₦500,000 warns if it breaches buffer.
7. Capital into Salon is not household lifestyle spend.
8. Health score is explainable component-by-component.
9. Household A cannot read Household B.
10. No mock-mode flag exists in the architecture.
11. AI never authors a number the engines did not produce.
12. Six-month seed shocks do not corrupt balances.
13. Founding-family concepts (tithe, baby, salon, etc.) appear only as household configuration / seed data — never as engine vocabulary.

---

## 36. Purchase check

Input: amount, optional category, optional account.

Against Current STS and minimum buffer:

**₦180,000 example**

```text
PURCHASE CHECK
Purchase: ₦180,000
Current cash              ₦1,400,000
Committed                 −₦850,000
Safe to spend              ₦550,000
Purchase                  −₦180,000
Remaining safe-to-spend    ₦370,000
✓ Affordable
✓ No obligation affected
✓ Budget remains intact
```

**₦500,000 example** (when remaining would breach minimum buffer)

```text
⚠️ CAUTION
This purchase would reduce your safe-to-spend
balance below your family's minimum buffer.
University fund would remain safe.
Recommended action: Delay / reduce / use surplus.
```

Severity:

- `healthy` — remaining current STS ≥ minimum buffer, no obligation impact
- `warning` — remaining current STS < minimum buffer, or category would exceed budget
- `critical` — remaining current STS < 0 or a protected/critical obligation would be raided

---

## 37. Financial calendar

Month view of:

- Obligation occurrences
- Recurring bills
- Scheduled fund contributions / investments
- Period close / monthly review

List header: **Financial obligations due in next 30 days.**

---

## 38. Giving architecture

```text
GIVING (configurable)
│
├── Household-defined kinds (defaults are suggestions only)
│     e.g. Tithe, Church, Charity, Family support, Gifts, Custom
├── Each may be: fixed | percentage | limit-bounded
├── Optional dual-partner approval above a limit
└── Actual spending tracked against policy
```

Giving beyond configured limits must surface as a warning (and optional dual approval). It must not silently consume obligation or sinking-fund money. The engine does not require any household to practice religious or cultural giving.

---

## 39. Business accounting

Any household business (seed example: Salon) is a separate entity.

```text
BUSINESS
├── Revenue
├── Expenses
├── Employees
├── Assets
├── Capital
├── Family Contributions
├── Withdrawals
└── Profit/Loss
```

Household → business: `capital_contribution`.  
Business → household: `withdrawal`.

Questions the module must answer:

- How much has the family invested in this business?
- Has the business generated a return?

---

## 40. Automation engine

Rules-as-data, executed by services and a scheduler (Phase 10).

```text
WHEN salary / income is recognized
  → calculate allocations
  → fund sinking funds
  → allocate savings and investment
  → update budgets
  → update safe-to-spend
  → generate alerts

WHEN obligation due date approaches
  IF fund < required amount → alert household

WHEN category reaches 80% of budget → warning
WHEN category exceeds budget → overspending alert
```

Scheduler is idempotent. Alert deduplication key: `(household_id, type, related_entity, period)`.

---

## 41. Family Financial Constitution

A first-class product concept: the household's declared answer to **"How should money work here?"**

It is not a separate engine. It is the named, reviewable set of configuration that the allocation waterfall, obligations, budgets, giving policies, and minimum buffer already express.

### Onboarding prompt

> How does your family want money to work?

### Example (founding household — configuration only)

```text
FAMILY FINANCIAL CONSTITUTION

Income
↓
1. Priority giving / first allocation rule (e.g. Tithe) — if configured
↓
2. Essential obligations
↓
3. Family needs / budgets
↓
4. Emergency reserve
↓
5. Savings
↓
6. Investments
↓
7. Personal spending
↓
8. Additional giving
```

Another household may omit giving, reorder priorities, or use fixed amounts. IPÌLẸ̀ executes that household's constitution.

### Operating loop

```text
Configured Plan (constitution)
       ↓
Actual Behaviour
       ↓
Patterns
       ↓
Insights / Recommendations
       ↓
Household chooses whether to change rules
```

IPÌLẸ̀ must not silently rewrite the constitution. AI and insights explain variance against it; only explicit household actions mutate rules.

### Acceptance

- Constitution is visible as the ordered active allocation rules + key policies (buffer, giving limits, mandatory flags).
- Seed / founding examples in §28 are fixtures for Tenant #1, not product defaults forced on every household.

---

## Document control

| Version | Date | Notes |
|---|---|---|
| 1.0.0 | 2026-09-14 | Complete product specification. Implementation must phase from this document. |
| 1.1.0 | 2026-09-14 | IPÌLẸ̀ brand; Tenant #1 ≠ product definition; litmus test; Family Financial Constitution; configurable giving kinds; Family Finance → Wealth → Family Office journey; decision-first UX principles. |

Changes to financial formulas, tenancy, or security require a version bump and an update to engine tests before code changes land.
