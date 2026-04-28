# DESIGN.md Usage for Piranha Global

`DESIGN.md` is the permanent visual contract for this repository.

## Reading order

1. Read the root `DESIGN.md`.
2. Read `.claude/CLAUDE.md` for agent governance and squad rules.
3. Use the brand-specific guidance in `knowledge/brand/` when you need a concise operational reference.

## What it controls

- Colors
- Typography
- Spacing
- Corner radius
- Component patterns
- Layout discipline
- Brand usage by sub-brand
- Visual rules for campaigns, dashboards, Shopify, and internal tools

## Practical usage

- Use token references exactly as written.
- Do not invent alternate palette values for convenience.
- Keep red reserved for symbols, emphasis, and primary brand moments.
- Prefer the defined component tokens for buttons, cards, badges, tables, banners, and alerts.

## Validation workflow

- Run `npm run design:lint`.
- Fix broken references or invalid token paths before building UI.
- Run the export commands when the codebase needs Tailwind or DTCG output.
- Check contrast any time a component uses background and text color together.

## Governance workflow

- Before a visual task, identify the relevant brand first.
- If the work is for a sub-brand, map it to the correct part of the architecture.
- If the solution needs a visual exception, document the reason and update `DESIGN.md` rather than bypassing the system.
- Treat `DESIGN.md` as a living contract, not a one-off brief.
