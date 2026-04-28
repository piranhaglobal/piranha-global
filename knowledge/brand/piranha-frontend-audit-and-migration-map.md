# Front-End Audit and Migration Map

Audited against the root `DESIGN.md` and the current repository structure.

## Scope

This audit covers the main visible front-end surfaces in the repository and classifies them by brand relevance, design-system readiness, and migration priority.

## Surfaces Found

### 1. `piranha-squad-ui`

- Stack: React 19 + Vite + Tailwind + React Flow
- Entry point: [piranha-squad-ui/src/App.jsx](/Users/sofianogueiro/Documents/piranha-global/piranha-squad-ui/src/App.jsx)
- Supporting styles: [piranha-squad-ui/src/index.css](/Users/sofianogueiro/Documents/piranha-global/piranha-squad-ui/src/index.css)
- Nature: internal control plane for squads, dashboard, builder, HQ, login and chat views
- Current visual state: strongly custom, dark, tactical, but built with hardcoded grays, blues, greens and component-level styling
- Design-system readiness: medium
- Risk: high visual drift because most surfaces still encode theme values directly in component files

### 2. `squads/piranha-dev/projects/piranha-leads/atlas`

- Stack: React + Vite + TypeScript + Tailwind
- Entry point: [squads/piranha-dev/projects/piranha-leads/atlas/src/App.tsx](/Users/sofianogueiro/Documents/piranha-global/squads/piranha-dev/projects/piranha-leads/atlas/src/App.tsx)
- Supporting styles: [squads/piranha-dev/projects/piranha-leads/atlas/src/index.css](/Users/sofianogueiro/Documents/piranha-global/squads/piranha-dev/projects/piranha-leads/atlas/src/index.css)
- Nature: private operations portal for scraping, database and settings
- Current visual state: more disciplined than `piranha-squad-ui`, but still based on its own color tokens and font stack
- Design-system readiness: medium-high
- Risk: theme fragmentation because it defines a separate palette and typography system

### 3. `squads/piranha-design/projects/piranha-workstation`

- Stack: static HTML/CSS/JS preview and section frames
- Main preview entry: [squads/piranha-design/projects/piranha-workstation/preview/index.html](/Users/sofianogueiro/Documents/piranha-global/squads/piranha-design/projects/piranha-workstation/preview/index.html)
- Section frames: `frames/section1` through `frames/section12`
- Nature: product/brand landing page for the Workstation 1.0 and its supporting editorial sections
- Current visual state: visually strong, but implemented with hardcoded CSS, raw font imports, and local art-direction choices
- Design-system readiness: medium
- Risk: brand inconsistency across generated sections because each frame can drift independently

## What Is Most Aligned Already

- Strong hero-led product storytelling in workstation surfaces
- Technical/dashboard structure in `piranha-squad-ui`
- Data-heavy operational patterns in `atlas`
- Clear separation between editorial, technical and utility views

## What Is Misaligned

- Hardcoded colors outside `DESIGN.md`
- Independent font stacks, especially in `piranha-squad-ui` and `atlas`
- Repeated use of generic dark SaaS palettes
- Excessive per-component styling instead of shared primitives
- Border radius, shadows and spacing not governed by the root design system
- SVG, card and banner styles that are visually close but not token-driven

## Migration Priority

### Priority 1: `piranha-squad-ui`

Why first:

- It is the most visible internal front-end.
- It mixes dashboard, office, builder and chat flows in one surface.
- It currently contains the most obvious custom styling drift.

What to migrate:

- Root shell colors and typography
- Primary navigation and tab states
- Dashboard cards
- Builder panels
- Login / access states
- Alerts, badges and status chips

### Priority 2: `atlas`

Why second:

- It is already structured as a modern app and will be easier to normalize.
- It has clear surface types: login, topbar, tabs, data grid, drawer, settings.

What to migrate:

- Global theme variables
- Login screen
- Header / tab system
- Tables, drawers and controls
- Status colors and data emphasis

### Priority 3: `piranha-workstation`

Why third:

- It is a brand-facing product page and benefits directly from the identity system.
- It has strong editorial structure that can be aligned without breaking the art direction.

What to migrate:

- Section spacing and type scale
- CTA treatments
- Product spec blocks
- Editorial blocks and banners
- Color tokens for black, white and red accents

### Priority 4: Section frames

Why fourth:

- They are valuable source material but not the main live surface.
- They should be normalized after the main product and dashboard surfaces are stable.

What to migrate:

- Shared section primitives
- Reusable typography and layout rules
- Standardized hero, specs and mission blocks

## Recommended Shared Primitives

- `AppShell`
- `Topbar`
- `SideNav`
- `TabBar`
- `Hero`
- `Card`
- `MetricCard`
- `StatusBadge`
- `TechnicalTable`
- `LoginPanel`
- `SectionBanner`
- `EmptyState`
- `Alert`

## Recommended Implementation Order

1. Export `DESIGN.md` tokens into the active styling system used by each app.
2. Replace hardcoded colors and typography with token-backed variables.
3. Centralize repeated primitives into a shared component layer.
4. Apply the shared primitives to the highest-priority surfaces first.
5. Add visual QA for contrast, spacing and component consistency.

## Notes

- The root `DESIGN.md` is the system of record for visual identity.
- Existing agent instructions in `.claude/CLAUDE.md` already enforce governance and should remain in place.
- Any visual exception should be justified as an update to `DESIGN.md`, not as an isolated one-off style fix.
