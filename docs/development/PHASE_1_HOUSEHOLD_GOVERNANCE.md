# Phase 1 — Household governance and financial privacy

**Status:** Implementation in progress on `feat/phase-1-household-governance`. Do not deploy until CI, migration validation, and staging acceptance are complete.

## Implemented work packages

| ID | Capability | Current implementation |
|---|---|---|
| HG-01 | Personal/shared account management | Owners and partners manage household accounts; members can create and update only their own personal accounts. |
| HG-02 | Personal/shared transaction management | Personal transactions are tied to the account owner; shared transactions use shared accounts. Cross-scope transfers are rejected until paired ledger entries exist. |
| HG-03 | Ownership and visibility enforcement | Query filters enforce household, scope, and member ownership. Transaction references are checked against the active household. |
| HG-04 | Member permission management | Owner-managed JSON permission grants are available for contribution and obligation visibility. Viewer/advisor defaults remain restricted; explicit grants are required. |
| HG-05 | Member-scoped financial aggregates | Member overview and `/member/financial-summary` use only shared and own personal accounts/transactions. Household-wide wealth and Safe-to-Spend remain owner/partner-only. |
| HG-06 | Contribution agreement management | Owners/partners create and update agreements; members see only their own agreements unless explicitly granted broader visibility. |
| HG-07 | Contribution schedules and payment records | Schedule engine supports weekly, biweekly, monthly, quarterly, annual and one-off cadence. Members can record their own payments. |
| HG-08 | Contribution history and audit trails | Agreement create/update and contribution record creation write audit events. Contribution records are immutable ledger evidence. |

## Permission model

The `household_members.permissions` JSON field currently supports:

- `view_all_contributions`
- `view_all_obligations`

Both default to false. Only the household owner can change member roles and grants. Partner access remains governed by the existing partner role. Viewer and advisor remain read-only; grants permit additional read visibility, not write access.

## Contribution integrity

- Agreement member must belong to the active household.
- Agreement dates and cadence are validated.
- Records must be within the agreement period and the agreement must be active.
- A linked transaction must belong to the active household, be an income transaction, and match the amount/currency.
- A transaction can be linked to only one contribution record.
- Members may link only their own income transactions.
- All record creation is audited.

## Obligation visibility

- Owners/partners see all household obligations.
- Members see shared obligations and obligations assigned to themselves.
- Viewers/advisors see shared obligations only.
- An explicit `view_all_obligations` grant expands read visibility.
- The same rules apply to obligation detail, calendar, and overview upcoming obligations.

## Financial summary contract

`GET /api/v1/member/financial-summary`

Optional query parameters: `period_start`, `period_end`.

Returns the member's visible active account count, cash balance across visible liquid accounts, income, expenses, net cash flow, and transaction count for the selected period. It does not include household-only assets, liabilities, investments, wealth snapshots, or Safe-to-Spend calculations because those entities do not yet have owner/member scope metadata.

## Remaining Phase 1 acceptance gate

- [ ] Latest branch CI passes: Ruff, dependency audit, backend tests, frontend checks, and release acceptance.
- [ ] Verify all member role permission grants and default-deny behavior for viewer/advisor.
- [ ] Verify member account CRUD and transaction list/detail/update isolation end-to-end.
- [ ] Verify contribution record linked-transaction validation, duplicate prevention, and audit events.
- [ ] Verify all obligation visibility paths (list, detail, calendar, overview) for each role.
- [ ] Validate full Alembic chain through `0019_member_permissions` on a disposable database branch.
- [ ] Apply migrations to staging with the matching application release and verify rollback.
- [ ] Obtain staging acceptance before production deployment.

## Explicitly out of scope

- Household-wide net-worth and Safe-to-Spend for members.
- Member ownership metadata for assets, investments, and liabilities.
- Cross-scope transfers between personal and shared accounts.
- Advisor write access.
- Any new inbound email bank-alert development.
