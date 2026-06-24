---
name: web-accessibility
description: Accessibility for web interfaces to WCAG 2.2 AA. Semantic HTML, keyboard operability, focus management, ARIA used correctly, colour contrast, accessible forms and images, reduced-motion, and screen-reader-minded testing. Use when building or auditing web UI, components, or pages for users of assistive technology.
---

# Web Accessibility

Make web interfaces usable by people who navigate with a keyboard, a screen reader, voice control, or a magnifier.
The target is WCAG 2.2 AA, treated as a default, not a final-sprint audit.

---

### When to activate

- Building or reviewing any web UI component, page, or flow.
- Auditing an existing interface for accessibility.
- Designing forms, modals, navigation, or any interactive widget.

---

### Semantic structure first

- Use the semantic element that means what you need: `button` for actions, `a` for navigation, `nav`, `main`,
  `header`, `ul`, `table`, and real headings in order. The browser gives you focus, keyboard behaviour, and a role
  for free.
- Reach for ARIA only to fill a gap the platform cannot, never to paper over non-semantic markup. A `div` with
  `role="button"` and hand-wired key handlers is a worse button than `button`. The first rule of ARIA is do not use
  ARIA when a native element will do.
- Give each page one `h1` and a logical heading hierarchy with no skipped levels; screen-reader users navigate by
  heading.

---

### Keyboard and focus

- Every interactive control is reachable and operable by keyboard alone, in a logical tab order. If a mouse can do
  it, the keyboard must too.
- Keep a visible focus indicator. Never remove the focus outline without replacing it with something at least as
  clear.
- Manage focus on change: move focus into an opened dialog and trap it there, return it to the trigger on close, and
  move focus to the new content (or a status region) on a client-side route change.
- No keyboard trap: a user who tabbed in must be able to tab out.

---

### Perceivable content

- Meet contrast minimums: 4.5:1 for normal text, 3:1 for large text and for meaningful user-interface and graphical
  boundaries. Never use colour as the only way to convey meaning; pair it with text, shape, or an icon.
- Give every meaningful image a text alternative that conveys its purpose. Mark a purely decorative image with an
  empty alt so assistive tech skips it.
- Respect the user's reduced-motion preference: gate non-essential animation behind `prefers-reduced-motion`.
- Make tap and click targets large enough to hit comfortably.

---

### Forms

- Associate a real label with every form control. Placeholder text is not a label.
- Tie an error message to its field programmatically and announce it, so a screen-reader user learns what failed and
  why, not just that something did.
- Group related controls (a set of radios, a fieldset) with an accessible name.

---

### Internationalisation and testing

- Build translation-ready from the start: route user-facing text through one localisation layer, set the document
  language, and do not bake text into images.
- Automated scanners catch only a fraction of real barriers. Test the keyboard path end to end and listen to the flow
  with a screen reader before calling it accessible.
