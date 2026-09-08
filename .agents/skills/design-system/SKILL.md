---
name: design-system
description: "Build and audit a design system: token architecture and naming, spacing rhythm, stylesheet organisation, Tailwind v4 CSS-first theming, dark mode, and visual-consistency review. Use when you say \"set up design tokens\", \"audit this UI for consistency\", \"there are forty shades of grey in this codebase\", \"migrate us to Tailwind v4 @theme\", or \"review this PR for styling drift\". Not for choosing the visual direction itself, use `frontend-design`."
license: Apache-2.0
---

# Design System

Token architecture, stylesheet structure, and consistency auditing for a codebase's visual layer. This skill decides
where a value lives and what it is called, not what the interface should look like.

Baseline: Tailwind CSS v4, which is configured in CSS through `@theme` and no longer reads `tailwind.config.js`.

---

### When to activate

- Starting a project that needs a design system.
- Auditing an existing codebase for visual consistency.
- Preparing a redesign and needing an inventory of what is already there.
- Diagnosing a UI that looks wrong without an obvious cause.
- Reviewing a pull request that touches styling.
- Migrating a Tailwind v3 configuration to the v4 CSS-first setup.

---

### When not to activate

- Choosing the visual direction, composition, typography voice, and motion direction. Use `frontend-design`.
- Contrast ratios, focus indicators, target sizes, and reduced motion. Use `web-accessibility`.
- React component structure and animation implementation. Use `frontend-patterns`.
- Angular component styling and view encapsulation. Use `angular`.
- Next.js rendering and routing. Use `nextjs-app-router-patterns`.

---

### Working modes

This skill runs in one of three modes. Say which one you want, or the intent will be inferred from the request.

Generate builds a system from what the codebase already does. Scan the CSS, Tailwind classes, and styled-components
for existing values, extract the colours, type scale, spacing, radii, shadows, and breakpoints actually in use, then
propose a consolidated token set with a reason for each decision. The output is a written design document, a token
file in both JSON and CSS custom properties, and a self-contained preview page that renders every token so the set
can be reviewed without running the application.

Audit scores an existing interface across ten dimensions, each out of ten: colour consistency, type hierarchy,
spacing rhythm, component consistency, responsive behaviour, dark mode completeness, purposefulness of animation,
accessibility, information density, and polish, meaning hover, transition, loading, and empty states. Every score
comes with concrete examples and a fix pinned to a file and line. A score with no file reference is not a finding.

Slop check hunts the tells of generic generated design: gradients on everything, purple-to-blue defaults, glass
morphism with no purpose, rounded corners on elements that should be square, animation triggered by every scroll, a
centred hero over a stock gradient, and a system font stack with no personality. Report each hit with its location
and the direction it undermines.

---

### Put every visual value in a token

A hex code inside a component file cannot be themed, cannot be audited, and will be copied slightly wrong the next
time someone needs it. Define the value once and reference it everywhere.

```css
/* PASS: tokens/colors.css owns the values */
:root {
  --color-primary-500: #2563eb;
  --color-surface-default: #ffffff;
  --color-text-primary: #111827;
  --color-feedback-error: #dc2626;
}
```

```tsx
// PASS: the component references the token
<Button style={{ background: 'var(--color-primary-500)' }} />

// FAIL: the value is welded into the component
<Button style={{ background: '#2563eb' }} />
```

---

### Name tokens by category, variant, and scale

A token name describes the role, never the value. A name carrying a pixel count or a colour word breaks the moment
the value changes, which is the one thing tokens exist to make easy.

```css
/* PASS: role-based names that survive a value change */
--color-primary-500: #2563eb;
--color-surface-default: #ffffff;
--color-text-muted: #6b7280;
--shadow-card-default: 0 1px 3px rgb(0 0 0 / 0.1);
--radius-button-default: 0.5rem;
--spacing-section-gap: 4rem;
```

```css
/* FAIL: the name encodes the value, so it lies after the first change */
--padding-16px: 16px;
--color-blue: #2563eb;
--shadow-light-grey: 0 1px 3px rgb(0 0 0 / 0.1);
```

The shape is `--{category}-{variant}-{scale}`.

---

### Keep spacing on one rhythm

Every margin, padding, gap, and component height is a multiple of 8px, with 4px available for micro-adjustments such
as icon gutters and badge offsets. One rhythm is what makes unrelated components look like they belong together.

```css
/* PASS: on the rhythm */
padding: 16px 24px;
gap: 8px;
height: 48px;
```

```css
/* FAIL: values picked by eye, nothing lines up across components */
padding: 13px 19px;
gap: 6px;
height: 47px;
```

---

### Configure Tailwind v4 in CSS

Tailwind v4 removes `tailwind.config.js`. Configuration lives in the `@theme` block, and every token defined there
becomes both a CSS custom property and a Tailwind utility.

```css
/* PASS: styles/main.css, one source for the theme */
@import "tailwindcss";

@theme {
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
  --font-sans: "Inter Variable", sans-serif;
  --radius-md: 0.5rem;
  --spacing-18: 4.5rem;
}

@layer components {
  .btn-primary {
    @apply bg-[--color-primary] text-[--color-primary-foreground] rounded-[--radius-md] px-4 py-2;
  }
}
```

```javascript
// FAIL: a v3 config file that Tailwind v4 does not read
module.exports = {
  theme: { extend: { colors: { primary: '#2563eb' } } },
}
```

---

### Organise stylesheets with the 7-1 pattern

Seven folders and one entry file, so a reader knows where a rule lives before opening anything.

```text
styles/
├── abstracts/    Variables, functions, mixins, placeholders
├── base/         Reset, typography, base element styles
├── components/   Component styles, BEM named
├── layout/       Grid, header, footer, sidebar
├── pages/        Page-specific overrides
├── themes/       Light and dark token overrides
├── vendors/      Third-party overrides
└── main.scss     Imports only, no rules of its own
```

```scss
// PASS: abstracts holds logic only, and main.scss only imports
// abstracts/_spacing.scss
@function space($step) { @return $step * 8px; }

// FAIL: abstracts emitting CSS, and a rule written straight into main.scss
// abstracts/_spacing.scss
.container { padding: 16px; }
```

`abstracts/` emits no CSS, `components/` is never imported into `abstracts/`, and component classes follow
`.block__element--modifier`.

---

### Build dark mode on day one

Retrofitting dark mode means auditing every component for hardcoded colour. Building it in means overriding a handful
of semantic tokens. Do the second.

```css
/* PASS: semantic tokens, one override block per theme */
:root {
  --color-surface-default: #ffffff;
  --color-text-primary: #111827;
}

[data-theme="dark"] {
  --color-surface-default: #0f172a;
  --color-text-primary: #f8fafc;
}
```

```tsx
// FAIL: an arbitrary value that no theme can override
<div className="bg-[#ffffff] text-[#111827]" />
```

Both themes get exercised before a pull request lands, in a component workbench or the running application.

---

### Write mobile-first media queries

Base styles target the smallest viewport and each query adds to them. Mixing `min-width` and `max-width` produces
overlapping ranges and a cascade nobody can predict.

```css
/* PASS: mobile-first, one direction only */
.card { padding: 16px; }
@media (min-width: 768px) { .card { padding: 24px; } }
```

```css
/* FAIL: desktop-first, subtracting styles back out */
.card { padding: 24px; }
@media (max-width: 767px) { .card { padding: 16px; } }
```

Standard breakpoints: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`.

---

### Related skills

- `frontend-design` decides the visual direction the tokens express. Take the direction from there, then encode it
  here.
- `web-accessibility` owns contrast ratios, focus indicators, target sizes, and reduced motion. A palette that fails
  contrast is not a finished token set.
- `frontend-patterns` for the React components consuming these tokens.
- `angular` for the same consumption in an Angular codebase.
- `markdown-writer` for the design document the generate mode produces.
- `code-reviewer` for the styling-drift pass on a pull request.

---

### Checklist

- No hex value, font stack, radius, shadow, or spacing number appears outside the token files.
- Every token name describes a role, and no name contains a value or a raw pixel count.
- Spacing, sizing, and gaps are multiples of 8px, with 4px reserved for micro-adjustments.
- Tailwind configuration lives in `@theme`, and no `tailwind.config.js` remains.
- Stylesheets follow the 7-1 layout, `abstracts/` emits no CSS, and `main.scss` only imports.
- Dark mode is driven by semantic token overrides, and both themes have been viewed.
- Media queries are `min-width` only, from one shared breakpoint set.
- An audit finding names a file and a line, and a slop-check finding names the direction it undermines.
- Colour choices have been checked against the contrast rules in `web-accessibility`.
