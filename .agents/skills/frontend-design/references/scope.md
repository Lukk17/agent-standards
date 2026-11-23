# Scope

Companion reference for the [frontend-design](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building a landing page, dashboard, or app surface from scratch where the look matters.
- Upgrading a bland interface into something intentional and memorable.
- Translating a product concept into a concrete visual direction.
- Implementing a frontend where typography, composition, and motion carry the product.
- Reviewing a UI that works but reads as generic template output.
- The user says "make this page look designed", "this dashboard looks generic", "pick a visual direction for the landing page", "it works but it has no point of view" or "turn this card grid into something intentional".

---

### When not to activate

- Token architecture, theming, and stylesheet structure, and token-level slop such as raw hex values or off-scale
  spacing. Use `design-system`.
- Contrast ratios, focus indicators, target sizes, and reduced motion. Use `web-accessibility`.
- React component structure, hooks, and state. Use `react-patterns`.
- Next.js rendering, routing, and data. Use `nextjs-app-router-patterns`.
- Angular component and template work. Use `angular`.

---

### Related skills

- `design-system` owns tokens, theming, dark mode, spacing scales, and styling architecture, and its slop check finds
  token-level drift. This skill owns the judgement of whether a UI looks generic. Take the values from there, and add
  new ones there rather than inline.
- `web-accessibility` owns contrast ratios, focus indicators, target sizes, reduced motion, and form error wiring.
  A direction that fails those is not finished.
- `react-patterns` for React component structure and animation implementation.
- `nextjs-app-router-patterns` for Next.js rendering and routing under the design.
- `angular` for the same work in an Angular codebase.
- `seo` for the copy and metadata behind a marketing surface.
