---
name: design-system
description: 'Design tokens and naming, stylesheet layout, Tailwind theming, dark mode and UI audits. Use when the user says "set up design tokens" or "audit this UI for consistency". Not for visual direction, use `frontend-design`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Design System

Token architecture, stylesheet structure, and consistency auditing for a codebase's visual layer. This skill decides where a value lives and what it is called, not what the interface should look like.

---

### When not to activate

- Choosing the visual direction, composition, typography voice and motion direction, or judging whether a UI looks generic, use `frontend-design`.
- Running the pull request review itself, use `code-reviewer`, which pulls this skill in for the styling-drift pass.
- Contrast ratios, focus indicators, target sizes and reduced motion, use `web-accessibility`.

---

### Working modes

Say which mode you want, or the intent is inferred from the request.

- Generate: extract the colours, type scale, spacing, radii, shadows and breakpoints the codebase already uses, and propose a consolidated token set with a reason per decision, as a design document, a token file and a preview page.
- Audit: score ten dimensions out of ten. Every score carries examples and a fix pinned to a file and line, or it is not a finding.
- Slop check: report every value that bypasses a token, with its location and the token it bypasses. Whether a UI looks generic is a direction question for `frontend-design`.

---

### Rules

1. Put every visual value in a token, defined once and referenced everywhere, never a hex code in a component file.
2. Name tokens by role as `--{category}-{variant}-{scale}`, never by value, pixel count or colour word.
3. Every margin, padding, gap and component height is a multiple of 8px, with 4px for micro-adjustments.
4. A styling framework takes its theme from the tokens through one configuration source, so no second copy of a value exists.
5. Organise stylesheets in the 7-1 layout: `abstracts/`, `base/`, `components/`, `layout/`, `pages/`, `themes/` and `vendors/` behind one imports-only entry file, with component classes in BEM.
6. Build dark mode on day one by overriding semantic tokens per theme, never arbitrary values, and view both themes before a pull request lands.
7. Write mobile-first `min-width` queries only, on the breakpoints `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`.

---

### Reference files

| Task | Open |
| --- | --- |
| The three modes in full, the ten audit dimensions, and pass and fail code for tokens, naming, spacing, dark mode and media queries | [references/modes-and-tokens.md](references/modes-and-tokens.md) |
| The project uses Tailwind CSS: `@theme`, `@config`, a v3 config file, arbitrary values | [references/tailwind.md](references/tailwind.md) |
| The project writes its styles in Sass: the 7-1 folders in full, `main.scss`, what `abstracts/` may hold | [references/sass.md](references/sass.md) |
| A React component sets a visual value, or styled-components hold values | [references/react.md](references/react.md) |
| Before calling a token set, an audit or a styling change done | [references/checklist.md](references/checklist.md) |
