# Modes and Tokens

Contents:

- [Working modes](#working-modes)
- [Put every visual value in a token](#put-every-visual-value-in-a-token)
- [Name tokens by category, variant, and scale](#name-tokens-by-category-variant-and-scale)
- [Keep spacing on one rhythm](#keep-spacing-on-one-rhythm)
- [Build dark mode on day one](#build-dark-mode-on-day-one)
- [Write mobile-first media queries](#write-mobile-first-media-queries)

Companion reference for the [design-system](../SKILL.md) skill. Load it for the full description of the generate, audit and slop-check modes, and for the pass and fail code behind tokens, naming, spacing, dark mode and media queries. Tailwind is in [tailwind.md](tailwind.md), the 7-1 stylesheet layout in [sass.md](sass.md), and tokens inside a React component in [react.md](react.md).

---

### Working modes

This skill runs in one of three modes. Say which one you want, or the intent will be inferred from the request.

Generate builds a system from what the codebase already does. Scan the CSS, and every other place the project keeps visual values, such as utility classes and styles written in JavaScript,
for existing values, extract the colours, type scale, spacing, radii, shadows, and breakpoints actually in use, then
propose a consolidated token set with a reason for each decision. The output is a written design document, a token
file in both JSON and CSS custom properties, and a self-contained preview page that renders every token so the set
can be reviewed without running the application. What to scan in a Tailwind project is in [tailwind.md](tailwind.md), and in a React project in [react.md](react.md).

Audit scores an existing interface across ten dimensions, each out of ten: colour consistency, type hierarchy,
spacing rhythm, component consistency, responsive behaviour, dark mode completeness, purposefulness of animation,
accessibility, information density, and polish, meaning hover, transition, loading, and empty states. Every score
comes with concrete examples and a fix pinned to a file and line. A score with no file reference is not a finding.

Slop check hunts the token-level tells of a system nobody designed: raw hex values and one-off gradients in component
files, spacing and sizes off the scale, a radius or shadow defined once and never reused, a font stack declared inline
rather than as a token, and near-duplicate colours that should be one token. Report each hit with its location and the
token it bypasses. Whether the interface looks generic, meaning purple-to-blue defaults, glass morphism with no
purpose, or a centred hero over a stock gradient, is a direction question, and `frontend-design` owns it.

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

```css
/* PASS: the component stylesheet references the token */
.button { background: var(--color-primary-500); }

/* FAIL: the value is welded into the component */
.button { background: #2563eb; }
```

The same pair written in JSX is in [react.md](react.md).

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

```css
/* FAIL: a raw value in a component, which no theme can override */
.card { background: #ffffff; color: #111827; }
```

The same failure written as a Tailwind arbitrary value is in [tailwind.md](tailwind.md).

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
