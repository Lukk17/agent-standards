---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use when the user asks to build web components, pages, or applications and the visual direction matters as much as the code quality.
origin: ECC
---

# Frontend Design

Use this when the task is not just "make it work" but "make it look designed."

This skill is for product pages, dashboards, app shells, components, or visual systems that need a clear point of view instead of generic AI-looking UI.

## When To Use

- building a landing page, dashboard, or app surface from scratch
- upgrading a bland interface into something intentional and memorable
- translating a product concept into a concrete visual direction
- implementing a frontend where typography, composition, and motion matter

## Core Principle

Pick a direction and commit to it.

Safe-average UI is usually worse than a strong, coherent aesthetic with a few bold choices.

## Design Workflow

### 1. Frame the interface first

Before coding, settle:

- purpose
- audience
- emotional tone
- visual direction
- one thing the user should remember

Possible directions:

- brutally minimal
- editorial
- industrial
- luxury
- playful
- geometric
- retro-futurist
- soft and organic
- maximalist

Do not mix directions casually. Choose one and execute it cleanly.

### 2. Build the visual system

Define:

- type hierarchy
- color variables
- spacing rhythm
- layout logic
- motion rules
- surface / border / shadow treatment

Use CSS variables or the project's token system so the interface stays coherent as it grows.

### 3. Compose with intention

Prefer:

- asymmetry when it sharpens hierarchy
- overlap when it creates depth
- strong whitespace when it clarifies focus
- dense layouts only when the product benefits from density

Avoid defaulting to a symmetrical card grid unless it is clearly the right fit.

### 4. Make motion meaningful

Use animation to:

- reveal hierarchy
- stage information
- reinforce user action
- create one or two memorable moments

Do not scatter generic micro-interactions everywhere. One well-directed load sequence is usually stronger than twenty random hover effects.

## Strong Defaults

### Typography

- pick fonts with character
- pair a distinctive display face with a readable body face when appropriate
- avoid generic defaults when the page is design-led

### Color

- commit to a clear palette
- one dominant field with selective accents usually works better than evenly weighted rainbow palettes
- avoid cliché purple-gradient-on-white unless the product genuinely calls for it

### Background

Use atmosphere:

- gradients
- meshes
- textures
- subtle noise
- patterns
- layered transparency

Flat empty backgrounds are rarely the best answer for a product-facing page.

### Layout

- break the grid when the composition benefits from it
- use diagonals, offsets, and grouping intentionally
- keep reading flow obvious even when the layout is unconventional

## Anti-Patterns

Never default to:

- interchangeable SaaS hero sections
- generic card piles with no hierarchy
- random accent colors without a system
- placeholder-feeling typography
- motion that exists only because animation was easy to add

## Execution Rules

- preserve the established design system when working inside an existing product
- match technical complexity to the visual idea
- keep accessibility and responsiveness intact
- frontends should feel deliberate on desktop and mobile

## Quality Gate

Before delivering:

- the interface has a clear visual point of view
- typography and spacing feel intentional
- color and motion support the product instead of decorating it randomly
- the result does not read like generic AI UI
- the implementation is production-grade, not just visually interesting

---

## Accessibility & Visual Standards

### WCAG 2.2 Level AA (Required)

- Normal text: 4.5:1 contrast ratio minimum
- Large text (18pt / 14pt bold) and UI components: 3:1 minimum
- Use contrast checkers in design tools before finalising colour choices
- All interactive elements must have visible focus indicators (3:1 against adjacent colours)

### Touch Targets

Minimum **44×44 CSS pixels** for all interactive elements (WCAG 2.5.8).
For icon-only buttons, add invisible padding to reach the minimum — do not enlarge the visual icon.

### 8-Point Grid System

All margins, paddings, gaps, and component heights must be multiples of **8px**.
Use **4px** for micro-adjustments (icon gutters, badge offsets) only.

```css
/* PASS: GOOD — multiples of 8 */
padding: 16px 24px;
gap: 8px;
height: 48px;

/* FAIL: BAD — arbitrary values */
padding: 13px 19px;
gap: 6px;
```

### Semantic Color Palette — Design Tokens Required

Never use hardcoded hex values in component files. Define all colours as design tokens:

```css
/* tokens.css */
:root {
  --color-primary-500: #2563eb;
  --color-surface-default: #ffffff;
  --color-text-primary: #111827;
  --color-feedback-error: #dc2626;
}

[data-theme="dark"] {
  --color-surface-default: #0f172a;
  --color-text-primary: #f8fafc;
}
```

```tsx
/* PASS: GOOD — tokens */
<Button style={{ background: 'var(--color-primary-500)' }} />

/* FAIL: BAD — hardcoded */
<Button style={{ background: '#2563eb' }} />
```

### Mobile-First Responsive Design

- Write base styles for the smallest viewport first
- Use **`min-width`** media queries only (never `max-width`)
- Design breakpoints: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`

```css
/* PASS: GOOD — mobile-first */
.card { padding: 16px; }
@media (min-width: 768px) { .card { padding: 24px; } }

/* FAIL: BAD — desktop-first */
.card { padding: 24px; }
@media (max-width: 767px) { .card { padding: 16px; } }
```

### Dark Mode — Day One Requirement

Dark mode is **not optional**. Implement using semantic tokens (see above) from the start of every project:

- No hard-coded colour values in component CSS
- Use CSS custom properties (`var(--token)`) — never Tailwind arbitrary values like `bg-[#fff]`
- Test both themes in Storybook before PR

### Animations & Motion

All animations **must** respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Timing guidelines:**
- Micro-interactions (button hover, checkbox): 100–150ms
- Component transitions (drawer open, accordion): 200–300ms
- Page/route transitions: 300–500ms
- Never exceed 500ms for any UI transition

### Loading States

- Use **skeleton screens** instead of spinners for initial content load
- Spinners are acceptable only for background/inline operations (e.g., form submission)
- Set `aria-busy="true"` on the container while loading
- Never show a full-screen spinner for background operations

```tsx
// PASS: GOOD — skeleton
{isLoading ? <ArticleSkeleton /> : <ArticleCard article={article} />}

// FAIL: BAD — spinner blocks content area
{isLoading ? <FullPageSpinner /> : <ArticleCard article={article} />}
```

### Form UX Rules

- Validate on **blur** (field loses focus), not on submit
- On submit with errors: scroll to the first invalid field automatically
- Never use disabled submit buttons — show inline validation errors instead
- Link error messages with `aria-describedby` pointing to the error element ID
- Show error messages below the field, not in a toast

```tsx
<input
  id="email"
  aria-describedby={emailError ? 'email-error' : undefined}
  aria-invalid={!!emailError}
/>
{emailError && <p id="email-error" role="alert">{emailError}</p>}
```

### Defensive UI Patterns

- **Destructive actions**: require a confirmation dialog with explicit labelling ("Delete permanently", not "OK")
- **Reversible destructive actions** (e.g., archive, remove from list): show an undo toast (5-second window) instead of a blocking confirmation dialog
- **Irreversible actions**: always require typing the resource name or "DELETE" in a confirmation input

### Internationalisation (i18n) Layout Budgets

- Allow **40% text expansion** for translated strings when sizing containers
- Support **RTL** layouts using CSS logical properties (`margin-inline-start`, `padding-block-end`) — never use `margin-left`/`padding-right` for layout
- Use the `Intl` API for all number, date, and currency formatting — never hardcode locale-specific formats

```tsx
// PASS: GOOD
const formatted = new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(price)

// FAIL: BAD
const formatted = `€${price.toFixed(2)}`
```
