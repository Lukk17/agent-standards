---
name: frontend-design
description: 'Giving an interface a committed visual direction, covering composition, typography, colour, background atmosphere and motion. Use when the user says "make this page look designed", "this dashboard looks generic", "pick a visual direction for the landing page" or "it works but it has no point of view". Not for token architecture, theming and styling structure, use `design-system`.'
license: Apache-2.0
---

# Frontend Design

Direction and composition for interfaces that need a point of view, not just working markup. Use this when the task is
not "make it work" but "make it look designed", on landing pages, dashboards, app shells, and marketing surfaces.

---

### When to activate

- Building a landing page, dashboard, or app surface from scratch where the look matters.
- Upgrading a bland interface into something intentional and memorable.
- Translating a product concept into a concrete visual direction.
- Implementing a frontend where typography, composition, and motion carry the product.
- Reviewing a UI that works but reads as generic template output.
- The user says "turn this card grid into something intentional".

---

### When not to activate

- Token architecture, theming, and stylesheet structure, and token-level slop such as raw hex values or off-scale
  spacing. Use `design-system`.
- Contrast ratios, focus indicators, target sizes, and reduced motion. Use `web-accessibility`.
- React component structure, hooks, and state. Use `react-patterns`.
- Next.js rendering, routing, and data. Use `nextjs-app-router-patterns`.
- Angular component and template work. Use `angular`.

---

### Reference files

| Task | Open |
| --- | --- |
| Pass and fail HTML and CSS for direction, variables, composition, motion, type, palette and background | [references/visual-direction.md](references/visual-direction.md) |

---

### Rules

1. Commit to one direction before writing CSS: settle the purpose, audience, emotional tone, direction and the one thing the user should remember. Workable directions include brutally minimal, editorial, industrial, luxury, playful, geometric, retro-futurist, soft and organic, and maximalist. Do not blend them casually.
2. Name type hierarchy, colour, spacing rhythm, layout logic, motion rules and surface treatment once, in variables, and reuse them. Never invent a value per component.
3. Compose with intention: asymmetry for hierarchy, overlap for depth, whitespace for focus. Use a symmetrical card grid only when the content genuinely is a set of peers, and keep the reading flow obvious when the layout is unconventional.
4. Direct the motion: one staged sequence that reveals hierarchy, stages information, reinforces an action or creates one memorable moment, not scattered hover effects. Every animation respects the motion preference in `web-accessibility`.
5. Pair a distinctive display face with a readable body face on a design-led page, and let scale carry hierarchy rather than weight alone.
6. Weight the palette: one dominant field with selective accents that mean something. Avoid the purple-to-blue gradient on white unless the product calls for it. Where values live belongs to `design-system`, contrast to `web-accessibility`.
7. Give a product-facing background atmosphere (gradients, meshes, textures, noise, patterns, layered transparency) that stays behind the content.

---

### Anti-patterns

| Never default to | Do instead |
| --- | --- |
| Interchangeable SaaS hero sections | Lead with the one thing the user should remember |
| Generic card piles with no hierarchy | Give one item weight and demote the rest |
| Random accent colours with no system | One dominant field, one accent with a job |
| Placeholder-feeling typography | A display face with real scale contrast |
| Motion added because animation was easy | One directed sequence that stages the content |
| A new hex value per component | A named variable in the visual system |

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

---

### Checklist

- The direction is stated in one sentence and every visual decision matches it.
- Type hierarchy, colour, spacing, motion, and surface treatment live in named variables, not in component files.
- The composition has an entry point and a reading order, and no section defaults to an undecided card grid.
- Motion is one or two directed moments, not scattered micro-interactions.
- Colour has one dominant field and accents that carry meaning.
- The background contributes atmosphere without competing with the content.
- An existing product's design system is preserved rather than overridden.
- Technical complexity matches the visual idea, with no framework added for one effect.
- The result is deliberate on both desktop and mobile.
- Accessibility and responsiveness survived the redesign, checked against `web-accessibility`.
