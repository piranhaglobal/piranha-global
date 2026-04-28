---
version: alpha
name: Piranha Global Brand System
description: Persistent design system and brand governance for the Piranha Global ecosystem.
source: Brandbook Piranha Global 2023, version 03, 11/2023
colors:
  primary: "#000000"
  on-primary: "#FFFFFF"
  background: "#FFFFFF"
  foreground: "#000000"
  piranha-red: "#E2231A"
  piranha-red-dark: "#B21E28"
  grey-60: "#878787"
  graphite: "#111111"
  carbon: "#1A1A1A"
  steel: "#B8B8B8"
  concrete: "#E7E4DE"
  warm-white: "#F4F1EC"
  muted: "#6F6F6F"
  border: "#D8D2C8"
  danger: "#B21E28"
  success: "#1F7A4D"
  warning: "#C47A1D"
typography:
  display-xl:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 72px
    lineHeight: 0.9
    fontWeight: 600
    letterSpacing: -0.06em
  display-lg:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 56px
    lineHeight: 0.94
    fontWeight: 600
    letterSpacing: -0.05em
  h1:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 42px
    lineHeight: 1
    fontWeight: 600
    letterSpacing: -0.04em
  h2:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 32px
    lineHeight: 1.02
    fontWeight: 600
    letterSpacing: -0.035em
  h3:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 24px
    lineHeight: 1.08
    fontWeight: 600
    letterSpacing: -0.03em
  body-lg:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 18px
    lineHeight: 1.6
    fontWeight: 400
    letterSpacing: -0.01em
  body-md:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 16px
    lineHeight: 1.55
    fontWeight: 400
    letterSpacing: 0
  body-sm:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 14px
    lineHeight: 1.45
    fontWeight: 400
    letterSpacing: 0
  label-caps:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 12px
    lineHeight: 1.25
    fontWeight: 600
    letterSpacing: 0.12em
  technical:
    fontFamily: '"Suisse Int''l Mono", "IBM Plex Mono", "SFMono-Regular", monospace'
    fontSize: 12px
    lineHeight: 1.45
    fontWeight: 400
    letterSpacing: 0.04em
  caption:
    fontFamily: '"Suisse Int''l", "Inter", "Helvetica Neue", Arial, sans-serif'
    fontSize: 12px
    lineHeight: 1.35
    fontWeight: 400
    letterSpacing: 0.01em
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  "2xl": 48px
  "3xl": 64px
  "4xl": 96px
  "5xl": 128px
rounded:
  none: 0px
  sm: 2px
  md: 4px
  lg: 8px
  xl: 12px
  "2xl": 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-primary-hover:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-brand-primary:
    backgroundColor: "{colors.piranha-red}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-brand-primary-hover:
    backgroundColor: "{colors.piranha-red-dark}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-secondary:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-secondary-hover:
    backgroundColor: "{colors.concrete}"
    textColor: "{colors.foreground}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  button-ghost:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
  card-product:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  card-editorial:
    backgroundColor: "{colors.warm-white}"
    textColor: "{colors.foreground}"
    typography: "{typography.body-lg}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  card-technical:
    backgroundColor: "{colors.concrete}"
    textColor: "{colors.carbon}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.lg}"
  badge-brand:
    backgroundColor: "{colors.piranha-red}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  badge-technical:
    backgroundColor: "{colors.warm-white}"
    textColor: "{colors.graphite}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  badge-muted:
    backgroundColor: "{colors.grey-60}"
    textColor: "{colors.primary}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  badge-surface:
    backgroundColor: "{colors.border}"
    textColor: "{colors.foreground}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  badge-steel:
    backgroundColor: "{colors.steel}"
    textColor: "{colors.foreground}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  input-default:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  nav-link:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.none}"
    padding: "{spacing.xs}"
  hero-section:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.display-lg}"
    rounded: "{rounded.none}"
    padding: "{spacing.4xl}"
  specs-table:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  newsletter-block:
    backgroundColor: "{colors.warm-white}"
    textColor: "{colors.foreground}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.xl}"
  campaign-banner:
    backgroundColor: "{colors.piranha-red}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-caps}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
  alert-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  alert-error:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
  status-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-primary}"
    typography: "{typography.technical}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs}"
  meta-divider:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.none}"
    padding: "{spacing.xs}"
---

## Overview
Piranha Global is the parent brand for a technical, premium ecosystem spanning tattoo, piercing, supplies, R&D, and product. The visual language must feel industrial, precise, cultural, and credible without falling into tattoo clichés or generic streetwear styling.

### Brand Essence
The brand exists to elevate tattoo craft through higher expertise, sharper relevance, and better access to tools, product, and operational knowledge. Every interface should feel like a serious instrument for craft and commerce, not a decorative layer around it.

### Brand Architecture
- `Piranha Global`: parent brand, legacy, vision, governance, and the system-level identity.
- `Piranha Tattoo Supplies`: e-commerce, B2B, supplying, and professional distribution.
- `Piranha Tattoo Studios`: service, art, client experience, and direct contact with end customers.
- `Piranha LAB`: innovation, design, R&D, product development, and technical validation.
- `Piranha Originals`: owned products tied directly to the Piranha brand.
- `Meta / Workstation`: premium, industrial, ergonomic workstations and related product lines.
- `Revolution Needles`: traditional and cartridge needles with a premium focus on precision and performance.
- `Safe Tat`: mid-tier tattoo and piercing products that stay distinct from the core Piranha brand, per the brandbook.

### Logo Usage Principles
- Use the logo and symbol with discipline, strong clear space, and high contrast.
- Keep the core marks rooted in black, white, and the official Piranha reds.
- Never stretch, bevel, emboss, texture, rotate, or crowd the logo with decorative effects.
- Reserve red for the symbol, strong accents, and critical moments. It is not a background color for default UI.
- In mixed-brand contexts, the parent brand should remain the governing system and the sub-brand should only add specificity where needed.

## Colors
The official base is black, white, and red. The primary red, `#E2231A`, is the symbol color and the strongest accent. The darker red, `#B21E28`, supports deeper accents and critical states. Grey `#878787` must be used carefully and never as a substitute for the core identity.

Functional colors exist only for digital UI. They support status, readability, and operational clarity, but they do not replace the brand palette.

- Use `primary` and `foreground` for authoritative surfaces and text.
- Use `piranha-red` for the main symbol, primary CTA moments, and high-attention brand accents.
- Use `piranha-red-dark` for deep accents, destructive actions, or critical states.
- Use `graphite`, `carbon`, `steel`, `concrete`, `warm-white`, and `border` to build quiet, controlled surfaces.
- Use `success`, `warning`, and `danger` only where the UI needs semantic status.
- Keep contrast high and avoid decorative color mixing. Color should organize, not entertain.

## Typography
Suisse Int'l is the principal family. Inter and Helvetica Neue exist as operational fallbacks. Mono is reserved for data and technical surfaces, not for decorative style.

- Use semibold for titles, strong claims, and brand statements.
- Use regular for descriptive body copy.
- Use mono for dates, SKUs, specs, locations, technical labels, and operational data.
- Keep negative tracking on titles so the brand feels compressed, confident, and engineered.
- Increase tracking only for institutional labels, sub-brand signatures, or technical tags when the hierarchy benefits from it.
- `display-xl` and `display-lg` are for hero statements and parent-brand authority.
- `h1`, `h2`, and `h3` should stay clean, direct, and highly legible.
- `body-lg`, `body-md`, and `body-sm` should stay readable and restrained.
- `label-caps`, `technical`, and `caption` should be short, precise, and operational.

## Layout
The layout language is clean, disciplined, and hierarchy-first. Large titles are allowed to occupy real width. Margins should feel generous. Grids should remain consistent. Visual noise is a defect.

### Front-End Application Rules
- Build with strong hierarchy, clear flow, and minimal ornamentation.
- Do not invent colors, shadows, or roundedness outside the tokens.
- Do not use decorative gradients unless they solve a clear brand or usability problem.
- Do not use glassmorphism, neumorphism, gaming chrome, or generic SaaS visuals.
- Prioritize readability, conversion, and technical confidence over visual gimmicks.

### Shopify / E-commerce Rules
- Lead with specs, benefits, pricing, availability, and the CTA.
- Product cards must be clean, technical, and decision-oriented.
- Imagery should support trust and detail, not noise.
- Keep merchandising systematic: product, variant, stock, price, and proof.
- Use red sparingly so it remains a signal, not wallpaper.

### Internal Dashboard Rules
- Use compact, functional, technical UI.
- Favor dense but legible layouts with strong data grouping.
- Use mono for operational values, identifiers, and status.
- Avoid large decorative spaces that reduce task efficiency.
- Make state, priority, and error conditions obvious without dramatization.

### Campaign / Landing Page Rules
- Combine desire with technical precision.
- Keep one clear objective per page and one primary CTA.
- The hero should carry authority through photography, render, or strong typography.
- Campaign surfaces can be more expressive, but never chaotic.
- Always keep the brand system visible beneath the campaign layer.

## Elevation & Depth
Depth should feel engineered, not soft. Prefer borders, contrast, and spacing before shadow. When shadow is used, it should be subtle and functional.

- Avoid heavy drop shadows, glow effects, and layered noise.
- Avoid default UI depth systems that feel generic or bubbly.
- Use depth to separate surfaces, not to dramatize them.
- Red should not be used as a depth treatment.

### Motion Direction
Motion should feel controlled, precise, and slightly mechanical.

- Use short, purposeful transitions.
- Prefer opacity, translate, and border-state changes over elastic motion.
- Avoid bouncy easing, overshoot, or playful gimmicks.
- Motion should support clarity, feedback, and confidence.

## Shapes
The brand should not feel too soft. Corners are controlled, not rounded for comfort alone.

- Prefer `none`, `sm`, and `md` radii for most surfaces.
- Use `lg` and `xl` only when a component genuinely needs a calmer profile.
- Use `2xl` sparingly.
- Avoid pill-heavy systems except where the product pattern clearly calls for a capsule label.
- Keep geometry rectilinear, industrial, and practical.

### Photography Direction
Photography should feel tactile, craft-aware, and materially honest.

- Prioritize close-ups, tools, process, texture, skin, metal, and real studio conditions.
- Use images that communicate expertise, precision, and cultural credibility.
- Hero visuals should be strong enough to carry the page without additional decoration.
- Avoid cliché tattoo imagery: random skulls, flames, aggressive lettering, graffiti clutter, and generic streetwear tropes.
- Product imagery should be clean, detailed, and trustworthy.

## Components
Components must be built from the tokens above and should express the brand through restraint, not decoration.

- `button-primary` and `button-primary-hover` are for the main action. In brand-led contexts they may be black by default, and in high-urgency brand moments they may become red, but only if the surrounding surface stays disciplined.
- `button-secondary` and `button-ghost` support secondary actions without competing with the primary CTA.
- `card-product` should help users decide fast through clear composition and low visual noise.
- `card-editorial` can breathe more, but still needs sharp hierarchy and a premium surface.
- `card-technical` should be denser, more structured, and more operational.
- `badge-brand` should be short and confident. `badge-technical` should be short, mono, and informative.
- `input-default` should be clean, clear, and easy to scan.
- `nav-link` should feel lightweight and controlled, not loud.
- `hero-section` should support a strong title, a simple CTA, and a focal image or render.
- `specs-table` must be clear, high-contrast, and free of ornament.
- `newsletter-block` should stay direct, breathable, and consistent with the rest of the system.
- `campaign-banner` should be attention-grabbing without becoming noisy.
- `alert-warning` and `alert-error` should be semantically obvious and visually disciplined.

### AI Agent Rules
- Agents must use these tokens directly and not invent new colors, fonts, spacing, or shape logic.
- Agents must keep the brand architecture in mind before generating any interface.
- Agents must prefer exact token references over ad hoc style decisions.
- Agents should map output to the correct brand first: `Piranha Global`, `Piranha Tattoo Supplies`, `Piranha Tattoo Studios`, `Piranha LAB`, `Piranha Originals`, `Meta / Workstation`, `Revolution Needles`, or `Safe Tat`.
- If a design exception is necessary, the agent should explain the exception and propose a `DESIGN.md` update rather than quietly drifting off-system.

## Do's and Don'ts
### Do
- Use black, white, and red as the identity core.
- Keep typography direct, confident, and readable.
- Use plenty of whitespace where it improves hierarchy.
- Keep components simple, consistent, and token-driven.
- Use photography, spec tables, and precise copy to communicate value.
- Make technical information easy to scan.
- Favor brand clarity over stylistic novelty.

### Don't
- Do not use generic tattoo clichés, skull graphics, flames, or noisy grunge for their own sake.
- Do not create chaotic layouts, over-decorated hero sections, or random visual effects.
- Do not introduce unapproved colors, fonts, shadows, or radius scales.
- Do not use heavy shadows, glassmorphism, neumorphism, or gaming/cyberpunk aesthetics.
- Do not overload the interface with red. Red is an accent, symbol, and CTA signal.
- Do not replace technical clarity with hype or corporate filler.
- Do not make the parent brand feel less disciplined than its sub-brands.
