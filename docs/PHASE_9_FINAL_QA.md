# Phase 9 — Final frontend polish and QA

## Scope

This phase consolidates the visual and interaction system introduced across Phases 1–8. It is intentionally frontend-only: no API contract, authorization policy, ledger behavior, database schema, or migration is changed.

## Implemented

- Keep Sora as the typography system in both light and dark themes.
- Give the mobile primary navigation direct access to Home, Money, Plan, and Wealth; keep Family and secondary destinations in More.
- Keep More visually active when the current route is a secondary destination.
- Add explicit accessible names to desktop and mobile primary navigation.
- Allow Escape to dismiss the More panel, page search, and global Add menu.
- Strengthen visible keyboard focus and mobile navigation touch targets.
- Preserve reduced-motion preferences and improve narrow-screen table and heading behavior.

## Verification matrix

| Area | Automated coverage | Manual review still required |
|---|---|---|
| Type safety | CI frontend typecheck | None if CI passes |
| Existing behavior | Existing frontend unit tests | Verify key create/edit flows in a signed-in household |
| Production rendering | Next.js production build | Check browser console and hydration |
| Responsive layout | CSS breakpoint rules in source | Review 360px, 390px, 768px, 1024px and wide desktop |
| Navigation | Typecheck/build | Verify active states, More panel and route destinations |
| Keyboard | Focus styling and Escape handling | Tab order, skip link, dialogs, menus and focus return |
| Themes | Shared light/dark tokens | Review every workspace in both themes |
| Financial integrity | No financial or backend code changed | Verify empty/loading/error states do not imply fabricated zero balances |

## Release boundary

A successful CI run is necessary but does not replace visual browser testing with authenticated household data. No production deployment or production migration is authorized by this phase.
