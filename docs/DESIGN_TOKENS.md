# IPÌLẸ̀ design tokens

Source of truth for frontend visual foundations (Phase 0).

## Brand (locked)

| Name | Hex | Role |
|------|-----|------|
| Near Black | `#050807` | Brand plane, dark canvas, inverse text on gold |
| Deep Forest | `#003D35` | Primary accent / actions |
| Champagne Gold | `#C9A45C` | Accent only (CTAs, highlights, STS labels) |
| Warm White | `#F7F6F2` | Light canvas / inverse text |

Gold is an **accent**. Do not paint whole surfaces gold.

## Semantic CSS variables

Mapped in `app/globals.css` and Tailwind (`tailwind.config.ts`):

| Token | Tailwind | Use |
|-------|----------|-----|
| `--color-bg-canvas` | `canvas` | Page background |
| `--color-bg-surface` | `surface` | Panels |
| `--color-bg-subtle` | `subtle` | Secondary fills |
| `--color-bg-brand` | `brand` | Near-black brand plane |
| `--color-text-primary` | `ink` | Body / headings |
| `--color-text-secondary` | `muted` | Supporting text |
| `--color-text-inverse` | `inverse` | Text on dark/accent fills |
| `--color-accent-primary` | `accent` | Primary actions |
| `--color-accent-gold` | `gold` | Accent |
| `--color-accent-gold-bright` | `gold-bright` | Hover / emphasis |
| `--color-border` | `line` | Borders |
| `--color-input-bg` | `input` | Form fields |
| `--color-status-*` | `healthy` `warning` `critical` | Status |

## Theme

- Light / dark via `data-theme` on `<html>`
- Persist: `localStorage.ipile_theme`
- Toggle: `ThemeToggle`

## Typography

- Display: Cormorant Garamond (`font-display`)
- Sans: Source Sans 3 (`font-sans`)
- Financial figures: always `.tabular` + `MoneyAmount`

## UI primitives (Phase 1)

`components/ui/`: Button, Input, Label, Dialog, Sheet, Tabs, Toast  
`lib/utils.ts`: `cn()` (clsx + tailwind-merge)  
Icons: Lucide

## Layout (Phase 2)

`components/layouts/PageHeader`, `SectionHeader`, `ContentContainer`  
`components/shared/AppShell` (Lucide nav + Button actions)

## Financial kit (Phase 3–4)

`SafeToSpend`, `ObligationCard`, `DecisionCard`, `AccountSummary`, `TransactionRow`, `FinancialAlert` (+ `MoneyAmount`)  
Money + Plan pages compose `PageHeader` / kit components.

## Charts (Phase 5)

Lazy ECharts via `echarts-for-react`: `CashFlowChart`, `NetWorthChart`, `AllocationChart`  
Theme-aware colors from CSS tokens.

## Forms (Phase 6)

`react-hook-form` + `zod` schemas in `lib/forms.ts`  
Wired on `TransactionForm`, `BudgetForm`, `ObligationForm`.

## Intelligence polish (Phase 7)

Insights / Reports / Simulator use PageHeader, Tabs, DecisionCards, and charts where data exists.

## Tests (Phase 8)

`npm test` runs all `lib/*.test.ts` via `lib/run-tests.cjs`  
Coverage: money formatting, Zod schemas, `cn`, money deltas, decision routing, and financial kit helpers used by `DecisionCard` / `ObligationCard` / STS readiness.

## Remaining surfaces (Phase 9)

Family, Wealth, Calendar, Forecast, Business, Inbox, Settings, Help, Onboarding  
Kit: `CashFlowSummary`, `NetWorthSummary`, `IncomeSummary`, `GivingSummaryCard`, `DebtSummaryCard`, `InvestmentSummaryCard`, `TransactionRow`, `MoneyChange`

## Hardening (Phase 10)

Skip link + `#main-content`, `:focus-visible`, `prefers-reduced-motion`, nav `aria-current`, toast `aria-live`, `RecurringForm` RHF+Zod, CI full suite.

## Rules

1. Prefer Tailwind semantic colors (`bg-canvas`, `text-ink`, `border-line`) over raw hex.
2. New colors require a token update here first.
3. Money formatting only through `lib/money.ts` / `MoneyAmount`.
4. Prefer kit components over one-off money UI on Home and Money/Plan pages.
5. Charts answer questions; they do not invent figures.
6. Form money fields validate through `lib/forms.ts` schemas.
