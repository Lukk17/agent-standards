---
name: web-accessibility
description: 'Web accessibility to WCAG 2.2 AA: semantics, keyboard, focus, ARIA, contrast and forms. Use when the user says "is this component accessible" or "audit this page for WCAG". Not for visual design, use `frontend-design`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# Web Accessibility

Make web interfaces usable by people who navigate with a keyboard, a screen reader, voice control, or a magnifier. The target is WCAG 2.2 AA, treated as a default, not a final-sprint audit.

Written for WCAG 2.2 Level AA.

---

### When not to activate

- Choosing the visual direction a palette and type scale express, use `frontend-design`.
- Where token values live and what they are called, use `design-system`.
- Building the component, its state and its animation in a framework, use `react-patterns`, `angular` or `dart-flutter-patterns`.

---

### Rules

1. Use the native element that means what you need (`button`, `a`, `nav`, `main`, `header`, `ul`, `table`, real headings). Do not use ARIA when a native element will do, and never to paper over non-semantic markup.
2. One `h1` per page and a heading hierarchy with no skipped levels.
3. Every control is reachable and operable by keyboard alone, in a logical tab order, and a user who tabbed in can tab out.
4. Keep a visible focus indicator. Never remove an outline without a replacement at least as clear.
5. A dialog moves focus in, traps Tab inside, closes on Escape, and returns focus to its trigger. Prefer the native `dialog` with `showModal()` and hand-roll the trap only when you cannot.
6. Move focus on a client-side route change, to the new content or a status region.
7. Contrast: 4.5:1 for normal text, 3:1 for large text, meaningful UI and graphical boundaries, and the focus indicator. Never convey meaning by colour alone.
8. Every meaningful image has an alt that conveys its purpose, and a decorative one has an empty alt.
9. Gate non-essential animation behind `prefers-reduced-motion`.
10. Targets are at least 24 by 24 CSS pixels (WCAG 2.2 AA), designed toward 44 by 44, reached with padding rather than a bigger icon.
11. Every form control has a real label, never a placeholder alone. Group related controls in a `fieldset` with a `legend`.
12. Tie an error to its field with `aria-describedby` (several ids allowed, the error only while present) and `aria-invalid` in step, with a message that says how to fix it.
13. Route user-facing text through one localisation layer, set the document language, keep text out of images, and use CSS logical properties.
14. Scanners catch only a fraction of barriers: test the keyboard path end to end and listen with a screen reader before calling anything accessible.

---

### Reference files

| Task | Open |
| --- | --- |
| Pass and fail markup for semantics, focus, the dialog trap code, contrast, images, motion, targets, forms and i18n | [references/patterns.md](references/patterns.md) |
| Whether a neighbouring skill owns the job | [references/scope.md](references/scope.md) |
| Before calling a component, a page or an audit accessible | [references/checklist.md](references/checklist.md) |
