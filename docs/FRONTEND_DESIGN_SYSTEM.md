# IPÌLẸ̀ Frontend Design System

Status: implementation baseline for the premium frontend redesign.

## Design intent

A calm, premium household-finance experience. The marketing site uses an editorial, centred hero with atmospheric light forms. The authenticated product uses a clear workspace layout with a deep-forest navigation rail, warm-white canvas, refined cards, and high-contrast financial information.

The implementation preserves existing application routes, authentication, API calls, role-based access, financial calculations, and empty/error/loading states.

## Brand palette (locked)

| Token | Hex | Usage |
|---|---|---|
| Near Black | `#050807` | Primary text, dark surfaces, structure |
| Deep Forest | `#003D35` | Primary actions, navigation, key emphasis |
| Champagne Gold | `#C9A45C` | Restrained accents, highlights, focus and motion glow |
| Warm White | `#F7F6F2` | Main light canvas and inverse text |

Supporting semantic colours remain defined in `frontend/app/globals.css`. Gold must remain an accent, not a dominant surface.

## Typography

- Primary family: Sora, weights 300, 400, 500, 600, 700.
- Use Sora consistently for display and interface text.
- Desktop marketing hero: fluid 52–100px, tight tracking and approximately 1.02 line height.
- Authenticated page title: fluid 30–42px.
- Section headings: 20–27px.
- Body: 13–15px with comfortable line height.
- Supporting labels: 9–12px, with restrained uppercase tracking.
- Financial amounts retain tabular numeral treatment and existing MoneyAmount formatting.

Sora is the chosen implementation match for the reference's geometric, modern sans-serif character; it is not claimed to be the exact original font file from the reference video.

## Layout and components

- Marketing navigation: sticky, translucent warm-white surface with backdrop blur.
- Marketing hero: centred editorial composition, large headline, short supporting copy and pill-shaped primary action.
- Ambient hero treatment: layered radial gradients in Deep Forest and Champagne Gold, with slow, low-amplitude movement.
- Authenticated desktop: 248px navigation rail and flexible content canvas.
- Navigation rail: Deep Forest-to-Near-Black gradient, Warm White labels and restrained Gold active state.
- Authenticated top bar: sticky translucent Warm White.
- Cards: 12–14px radius, subtle borders and restrained shadows.
- Mobile: existing bottom navigation and add action retained; content padding and typography scale fluidly.

## Motion principles

- Slow ambient gradient breathing; no rapid flashing.
- Subtle hover elevation and small navigation movement.
- Progressive reveal for marketing sections.
- Existing chart animation and data presentation remain tied to real application data.
- Honour `prefers-reduced-motion` and retain visible keyboard focus.

## Data integrity and product safety

- Do not introduce sample financial values into authenticated product screens.
- Marketing/product-preview figures must be clearly illustrative.
- Preserve loading, empty, error, permission-denied and first-run states.
- Do not change backend contracts, household authorization, data access, or financial computations as part of visual work.

## Implementation locations

- Global tokens and responsive visual language: `frontend/app/globals.css`
- Font loading and document metadata: `frontend/app/layout.tsx`
- Marketing hero: `frontend/app/page.tsx`
- Marketing navigation and sections: `frontend/components/landing/LandingSections.tsx`
- Authenticated navigation and shell: `frontend/components/shared/AppShell.tsx`
- Shared page title hierarchy: `frontend/components/layouts/PageHeader.tsx`

## Validation

Run from `frontend/`:

```bash
npm run typecheck
npm test
npm run build
```

Review responsive layouts at desktop, tablet and mobile widths, including light and dark themes, before integration.
