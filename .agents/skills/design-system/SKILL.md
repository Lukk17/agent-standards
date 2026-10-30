---
name: design-system
description: 'Building and auditing a design system: token architecture and naming, spacing rhythm, stylesheet organisation, Tailwind v4 CSS-first theming, dark mode and visual-consistency review. Use when the user says "set up design tokens", "audit this UI for consistency", "migrate us to Tailwind v4 @theme" or "which styles bypass our tokens". Not for choosing the visual direction, use `frontend-design`.'
license: Apache-2.0
---

# Design System

Token architecture, stylesheet structure, and consistency auditing for a codebase's visual layer. This skill decides
where a value lives and what it is called, not what the interface should look like.

Written for Tailwind CSS v4, which is configured in CSS through `@theme` and no longer auto-detects `tailwind.config.js`.

---

### When to activate

- Starting a project that needs a design system.
- Auditing an existing codebase for visual consistency.
- Preparing a redesign and needing an inventory of what is already there.
- Diagnosing a UI that looks wrong without an obvious cause.
- Supplying the styling-drift criteria when a pull request that `code-reviewer` is reviewing touches styling.
- Migrating a Tailwind v3 configuration to the v4 CSS-first setup.
- The user says "there are forty shades of grey in this codebase" or "which styles in this change bypass our tokens".

---

### When not to activate

- Choosing the visual direction, composition, typography voice, and motion direction, or judging whether a UI looks
  generic. Use `frontend-design`.
- Running the pull request review itself. Use `code-reviewer`, which pulls this skill in for the styling-drift pass.
- Contrast ratios, focus indicators, target sizes, and reduced motion. Use `web-accessibility`.
- React component structure and animation implementation. Use `react-patterns`.
- Angular component styling and view encapsulation. Use `angular`.
- Next.js rendering and routing. Use `nextjs-app-router-patterns`.

---

### Reference files

| Task | Open |
| --- | --- |
| The three modes in full, and pass and fail code for tokens, naming, spacing, Tailwind v4, 7-1 layout, dark mode, media queries | [references/modes-and-tokens.md](references/modes-and-tokens.md) |

---

### Working modes

Say which mode you want, or the intent is inferred from the request.

- Generate: extract the colours, type scale, spacing, radii, shadows and breakpoints the codebase already uses, and propose a consolidated token set with a reason per decision. Output a design document, a token file in JSON and CSS custom properties, and a self-contained preview page rendering every token.
- Audit: score ten dimensions out of ten (colour, type hierarchy, spacing rhythm, component consistency, responsive behaviour, dark mode, purposeful animation, accessibility, information density, polish). Every score carries examples and a fix pinned to a file and line, or it is not a finding.
- Slop check: report raw hex values and one-off gradients in components, off-scale spacing and sizes, a radius or shadow used once, inline font stacks, and near-duplicate colours, each with its location and the token it bypasses. Whether a UI looks generic is a direction question for `frontend-design`.

---

### Rules

1. Put every visual value in a token, defined once and referenced everywhere, never a hex code in a component file.
2. Name tokens by role as `--{category}-{variant}-{scale}`, never by value, pixel count or colour word.
3. Every margin, padding, gap and component height is a multiple of 8px, with 4px for micro-adjustments.
4. Tailwind v4 configuration lives in `@theme`, where each token becomes a custom property and a utility. v4 does not auto-detect `tailwind.config.js`, but `@config` can still load one, so search for `@config` before treating a config file as dead.
5. Organise stylesheets 7-1: `abstracts/`, `base/`, `components/`, `layout/`, `pages/`, `themes/`, `vendors/` and an imports-only `main.scss`. `abstracts/` emits no CSS, `components/` is never imported into it, and component classes are BEM.
6. Build dark mode on day one by overriding semantic tokens per theme, never arbitrary values, and view both themes before a pull request lands.
7. Write mobile-first `min-width` queries only, on the breakpoints `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`.

---

### Related skills

- `frontend-design` decides the visual direction the tokens express. Take the direction from there, then encode it
  here.
- `web-accessibility` owns contrast ratios, focus indicators, target sizes, and reduced motion. A palette that fails
  contrast is not a finished token set.
- `react-patterns` for the React components consuming these tokens.
- `angular` for the same consumption in an Angular codebase.
- `markdown-writer` for the design document the generate mode produces.
- `code-reviewer` runs the pull request review and pulls this skill in for its styling-drift criteria.

---

### Checklist

- No hex value, font stack, radius, shadow, or spacing number appears outside the token files.
- Every token name describes a role, and no name contains a value or a raw pixel count.
- Spacing, sizing, and gaps are multiples of 8px, with 4px reserved for micro-adjustments.
- Tailwind configuration lives in `@theme`, and no `tailwind.config.js` remains.
- Stylesheets follow the 7-1 layout, `abstracts/` emits no CSS, and `main.scss` only imports.
- Dark mode is driven by semantic token overrides, and both themes have been viewed.
- Media queries are `min-width` only, from one shared breakpoint set.
- An audit finding names a file and a line, and a slop-check finding names the token it bypasses.
- Colour choices have been checked against the contrast rules in `web-accessibility`.
