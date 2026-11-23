# Scope

Companion reference for the [design-system](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Starting a project that needs a design system.
- Auditing an existing codebase for visual consistency.
- Preparing a redesign and needing an inventory of what is already there.
- Diagnosing a UI that looks wrong without an obvious cause.
- Supplying the styling-drift criteria when a pull request that `code-reviewer` is reviewing touches styling.
- Migrating a Tailwind v3 configuration to the v4 CSS-first setup.
- The user says "set up design tokens", "audit this UI for consistency", "migrate us to Tailwind v4 @theme", "which styles bypass our tokens", "there are forty shades of grey in this codebase" or "which styles in this change bypass our tokens".

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

### Related skills

- `frontend-design` decides the visual direction the tokens express. Take the direction from there, then encode it
  here.
- `web-accessibility` owns contrast ratios, focus indicators, target sizes, and reduced motion. A palette that fails
  contrast is not a finished token set.
- `react-patterns` for the React components consuming these tokens.
- `angular` for the same consumption in an Angular codebase.
- `markdown-writer` for the design document the generate mode produces.
- `code-reviewer` runs the pull request review and pulls this skill in for its styling-drift criteria.
