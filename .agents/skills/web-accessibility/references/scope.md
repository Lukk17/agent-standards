# Scope

Companion reference for the [web-accessibility](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building or reviewing any web UI component, page, or flow.
- Auditing an existing interface for accessibility.
- Designing forms, modals, navigation, or any interactive widget.
- Deciding whether a pattern needs ARIA, and which role is correct.
- Checking a palette or a focus indicator against contrast minimums.
- Making images, target sizes and motion accessible: text alternatives, the 24 by 24 pixel minimum and reduced motion.
- The user says "is this component accessible", "audit this page against WCAG", "trap focus in this modal", "the screen reader skips my error message" or "check these colours for contrast".

---

### When not to activate

- Choosing the visual direction a palette and type scale express. Use `frontend-design`.
- Where token values live and what they are called. Use `design-system`.
- React composition, hooks, and animation implementation. Use `react-patterns`.
- Angular components, templates, and i18n wiring. Use `angular`.
- Flutter semantics and screen-reader support. Use `dart-flutter-patterns`.
- Search visibility and structured data. Use `seo`.

---

### Related skills

- `frontend-design` for the visual direction the palette and type scale express.
- `design-system` for where colour, spacing, and focus-ring tokens live.
- `react-patterns` for the React mechanics of keyboard handling and focus management.
- `angular` for the same work in an Angular codebase.
- `nextjs-app-router-patterns` for route changes, which are where focus is most often dropped.
- `dart-flutter-patterns` for the equivalent semantics work in Flutter.
- `e2e-testing` for driving the keyboard path in a browser as a regression test.
