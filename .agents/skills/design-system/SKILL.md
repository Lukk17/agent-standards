---
name: design-system
description: Use this skill to generate or audit design systems, check visual consistency, and review PRs that touch styling.
origin: ECC
---

# Design System — Generate & Audit Visual Systems

## When to Use

- Starting a new project that needs a design system
- Auditing an existing codebase for visual consistency
- Before a redesign — understand what you have
- When the UI looks "off" but you can't pinpoint why
- Reviewing PRs that touch styling

## How It Works

### Mode 1: Generate Design System

Analyzes your codebase and generates a cohesive design system:

```
1. Scan CSS/Tailwind/styled-components for existing patterns
2. Extract: colors, typography, spacing, border-radius, shadows, breakpoints
3. Research 3 competitor sites for inspiration (via browser MCP)
4. Propose a design token set (JSON + CSS custom properties)
5. Generate DESIGN.md with rationale for each decision
6. Create an interactive HTML preview page (self-contained, no deps)
```

Output: `DESIGN.md` + `design-tokens.json` + `design-preview.html`

### Mode 2: Visual Audit

Scores your UI across 10 dimensions (0-10 each):

```
1. Color consistency — are you using your palette or random hex values?
2. Typography hierarchy — clear h1 > h2 > h3 > body > caption?
3. Spacing rhythm — consistent scale (4px/8px/16px) or arbitrary?
4. Component consistency — do similar elements look similar?
5. Responsive behavior — fluid or broken at breakpoints?
6. Dark mode — complete or half-done?
7. Animation — purposeful or gratuitous?
8. Accessibility — contrast ratios, focus states, touch targets
9. Information density — cluttered or clean?
10. Polish — hover states, transitions, loading states, empty states
```

Each dimension gets a score, specific examples, and a fix with exact file:line.

### Mode 3: AI Slop Detection

Identifies generic AI-generated design patterns:

```
- Gratuitous gradients on everything
- Purple-to-blue defaults
- "Glass morphism" cards with no purpose
- Rounded corners on things that shouldn't be rounded
- Excessive animations on scroll
- Generic hero with centered text over stock gradient
- Sans-serif font stack with no personality
```

## Examples

**Generate for a SaaS app:**
```
/design-system generate --style minimal --palette earth-tones
```

**Audit existing UI:**
```
/design-system audit --url http://localhost:3000 --pages / /pricing /docs
```

**Check for AI slop:**
```
/design-system slop-check
```

---

## Styling Architecture

### SCSS 7-1 Architecture

Organise stylesheets into seven folders plus one main entry file:

```
styles/
├── abstracts/    # Variables, functions, mixins, placeholders
├── base/         # Reset, typography, base element styles
├── components/   # Component-specific styles (BEM)
├── layout/       # Grid, header, footer, sidebar
├── pages/        # Page-specific overrides
├── themes/       # Light/dark theme token overrides
├── vendors/      # Third-party library overrides
└── main.scss     # Import-only file; no styles here
```

Rules:
- `abstracts/` contains only SCSS logic — no output CSS
- Never import `components/` into `abstracts/`
- BEM naming in `components/`: `.block__element--modifier`

### Tailwind v4 — CSS-First Configuration

Tailwind v4 removes `tailwind.config.js`. Use the `@theme` block in your CSS:

```css
/* styles/main.css */
@import "tailwindcss";

@theme {
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
  --font-sans: "Inter Variable", sans-serif;
  --radius-md: 0.5rem;
  --spacing-18: 4.5rem;
}

/* Custom components go in @layer components */
@layer components {
  .btn-primary {
    @apply bg-[--color-primary] text-[--color-primary-foreground] rounded-[--radius-md] px-4 py-2;
  }
}
```

- No `tailwind.config.js` — all configuration lives in `@theme`
- Use CSS custom properties from `@theme` via `var(--token)` or the bracket shorthand `[--token]`
- Design tokens defined in `@theme` are automatically available as Tailwind utilities

### Design Token Naming Convention

```
--{category}-{variant}-{scale}

Examples:
--color-primary-500
--color-surface-default
--color-text-muted
--shadow-card-default
--radius-button-default
--spacing-section-gap
```

Never create tokens with hardcoded pixel values in the name (`--padding-16px` is wrong; `--spacing-4` is correct).
