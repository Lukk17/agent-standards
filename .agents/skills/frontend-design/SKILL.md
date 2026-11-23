---
name: frontend-design
description: 'Giving an interface a visual direction: composition, typography, colour and motion. Use when the user says "make this page look designed" or "this dashboard looks generic". Not for tokens, use `design-system`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Frontend Design

Direction and composition for interfaces that need a point of view, not just working markup. Use this when the task is not "make it work" but "make it look designed", on landing pages, dashboards, app shells, and marketing surfaces.

---

### When not to activate

- Token architecture, theming and stylesheet structure, and token-level slop such as raw hex values or off-scale spacing, use `design-system`.
- Contrast ratios, focus indicators, target sizes and reduced motion, use `web-accessibility`.
- Component structure, state, rendering and routing in a framework, use `react-patterns`, `nextjs-app-router-patterns` or `angular`.

---

### Rules

1. Commit to one direction before writing CSS: settle the purpose, audience, emotional tone, direction and the one thing the user should remember. Do not blend directions casually.
2. Name type hierarchy, colour, spacing rhythm, layout logic, motion rules and surface treatment once, in variables, and reuse them. Never invent a value per component.
3. Compose with intention: asymmetry for hierarchy, overlap for depth, whitespace for focus. Use a symmetrical card grid only when the content genuinely is a set of peers, and keep the reading flow obvious when the layout is unconventional.
4. Direct the motion: one staged sequence that reveals hierarchy, stages information, reinforces an action or creates one memorable moment, not scattered hover effects. Every animation respects the motion preference in `web-accessibility`.
5. Pair a distinctive display face with a readable body face on a design-led page, and let scale carry hierarchy rather than weight alone.
6. Weight the palette: one dominant field with selective accents that mean something. Avoid the purple-to-blue gradient on white unless the product calls for it. Where values live belongs to `design-system`, contrast to `web-accessibility`.
7. Give a product-facing background atmosphere (gradients, meshes, textures, noise, patterns, layered transparency) that stays behind the content.
8. Preserve an existing product's design system rather than overriding it, match technical complexity to the visual idea with no framework added for one effect, and make the result deliberate on both desktop and mobile.

---

### Reference files

| Task | Open |
| --- | --- |
| The list of workable directions, pass and fail HTML and CSS for direction, variables, composition, motion, type, palette and background, and the anti-pattern table | [references/visual-direction.md](references/visual-direction.md) |
| Whether a neighbouring skill owns the job | [references/scope.md](references/scope.md) |
| Before calling a design or a design review done | [references/checklist.md](references/checklist.md) |
