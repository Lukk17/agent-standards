---
name: web-accessibility
description: 'Accessibility for web interfaces to WCAG 2.2 AA: semantic HTML, keyboard operability, focus management, correct ARIA, colour contrast, accessible forms and images, target size and reduced motion. Use when the user says "is this component accessible", "audit this page against WCAG" or "trap focus in this modal". Not for the visual direction a palette expresses, use `frontend-design`.'
license: Apache-2.0
---

# Web Accessibility

Make web interfaces usable by people who navigate with a keyboard, a screen reader, voice control, or a magnifier.
The target is WCAG 2.2 AA, treated as a default, not a final-sprint audit.

Written for WCAG 2.2 Level AA.

---

### When to activate

- Building or reviewing any web UI component, page, or flow.
- Auditing an existing interface for accessibility.
- Designing forms, modals, navigation, or any interactive widget.
- Deciding whether a pattern needs ARIA, and which role is correct.
- Checking a palette or a focus indicator against contrast minimums.
- The user says "the screen reader skips my error message" or "check these colours for contrast".

---

### When not to activate

- Choosing the visual direction a palette and type scale express. Use `frontend-design`.
- Where token values live and what they are called. Use `design-system`.
- React composition, hooks, and animation implementation. Use `react-patterns`.
- Angular components, templates, and i18n wiring. Use `angular`.
- Flutter semantics and screen-reader support. Use `dart-flutter-patterns`.
- Search visibility and structured data. Use `seo`.

---

### Reference files

| Task | Open |
| --- | --- |
| Pass and fail markup for semantics, focus, the dialog trap code, contrast, images, motion, targets, forms and i18n | [references/patterns.md](references/patterns.md) |

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

### Related skills

- `frontend-design` for the visual direction the palette and type scale express.
- `design-system` for where colour, spacing, and focus-ring tokens live.
- `react-patterns` for the React mechanics of keyboard handling and focus management.
- `angular` for the same work in an Angular codebase.
- `nextjs-app-router-patterns` for route changes, which are where focus is most often dropped.
- `dart-flutter-patterns` for the equivalent semantics work in Flutter.
- `e2e-testing` for driving the keyboard path in a browser as a regression test.

---

### Checklist

- Every interactive element is a native control, or has a justified reason not to be.
- One `h1` per page, and no skipped heading levels.
- The whole flow is operable by keyboard, in a sensible order, with a visible focus indicator throughout.
- Every dialog moves focus in, traps it, closes on Escape, and restores focus to its trigger.
- Client-side route changes move focus to the new content or a status region.
- Text meets 4.5:1, and large text, UI boundaries, and the focus ring meet 3:1.
- No state or meaning is carried by colour alone.
- Every image has a purposeful alt, or an empty alt when decorative.
- Non-essential motion is gated behind `prefers-reduced-motion`.
- Targets are at least 24 by 24 CSS pixels, with padding rather than a bigger icon.
- Every field has a real label, and every error is linked with `aria-describedby` and `aria-invalid`.
- The document language is set and layout uses logical properties.
- The keyboard path and a screen-reader pass have both been run by hand, not only a scanner.
