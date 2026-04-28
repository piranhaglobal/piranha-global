# Piranha Global Brand System

This repository now uses `DESIGN.md` as the source of truth for visual identity, design system decisions, and UI governance.

## How it was created

- The system was derived from the Brandbook Piranha Global 2023, version 03, 11/2023.
- The root `DESIGN.md` translates the brandbook into tokens, rules, and application guidance that agents can apply consistently.
- The content is intentionally permanent and repository-level so it can govern new pages, components, dashboards, Shopify surfaces, internal tools, and generated scaffolds.

## Source of truth

- Primary source: Brandbook Piranha Global 2023, version 03, 11/2023.
- Secondary source of enforcement: the root `DESIGN.md`.
- Existing agent instructions in `.claude/CLAUDE.md` remain in place and now include governance rules that point back to `DESIGN.md`.

## How to use the tokens

- Use the exact token references from `DESIGN.md` rather than inventing new values.
- Colors, typography, spacing, and radius should flow through the design system.
- Component tokens exist to speed up consistent UI output:
  - `button-primary`
  - `card-product`
  - `specs-table`
  - `campaign-banner`
  - `alert-error`
- When implementing code, map the tokens into the project's actual styling system instead of hardcoding replacements.

## How to validate changes

- Run `npm run design:lint` before merging any visual change.
- Use `npm run design:export:tailwind` when you need Tailwind theme output.
- Use `npm run design:export:dtcg` when you need `tokens.json` output in DTCG format.
- For contrast-sensitive UI, verify that foreground/background combinations remain readable and that red is only used as an accent or critical signal.

## How to propose updates

- If a design exception is required, document why the current token set is insufficient.
- Propose the exact token or rule change needed in `DESIGN.md`.
- Keep updates additive and specific. Avoid broad visual drift.
- If a sub-brand needs a distinct treatment, explain how it fits the parent architecture before changing any visual rule.
