---
name: web-accessibility
description: Accessibility for web interfaces to WCAG 2.2 AA, covering semantic HTML, keyboard operability, focus management, correct ARIA, colour contrast, accessible forms and images, target size, and reduced motion. Use when you say "is this component accessible", "audit this page against WCAG", "trap focus in this modal", "the screen reader skips my error message", or "check these colours for contrast". Not for the visual direction a palette expresses, use `frontend-design`.
license: Apache-2.0
---

# Web Accessibility

Make web interfaces usable by people who navigate with a keyboard, a screen reader, voice control, or a magnifier.
The target is WCAG 2.2 AA, treated as a default, not a final-sprint audit.

Baseline: WCAG 2.2 Level AA, the current stable recommendation.

---

### When to activate

- Building or reviewing any web UI component, page, or flow.
- Auditing an existing interface for accessibility.
- Designing forms, modals, navigation, or any interactive widget.
- Deciding whether a pattern needs ARIA, and which role is correct.
- Checking a palette or a focus indicator against contrast minimums.

---

### When not to activate

- Choosing the visual direction a palette and type scale express. Use `frontend-design`.
- Where token values live and what they are called. Use `design-system`.
- React composition, hooks, and animation implementation. Use `frontend-patterns`.
- Angular components, templates, and i18n wiring. Use `angular`.
- Flutter semantics and screen-reader support. Use `dart-flutter-patterns`.
- Search visibility and structured data. Use `seo`.

---

### Semantic structure first

Use the element that means what you need: `button` for actions, `a` for navigation, plus `nav`, `main`, `header`,
`ul`, `table`, and real headings in order. The browser gives you focus, keyboard behaviour, and a role for free.
Reach for ARIA only to fill a gap the platform cannot, never to paper over non-semantic markup. The first rule of
ARIA is do not use ARIA when a native element will do.

```html
<!-- PASS: the platform supplies focus, Enter and Space, and the button role -->
<button type="button" onclick="openMenu()">Open menu</button>
```

```html
<!-- FAIL: not focusable, not operable by keyboard, and lying about its role -->
<div role="button" onclick="openMenu()">Open menu</div>
```

Give each page one `h1` and a heading hierarchy with no skipped levels, because screen-reader users navigate by
heading.

---

### Keyboard and focus

Every interactive control is reachable and operable by keyboard alone, in a logical tab order. If a mouse can do it,
the keyboard must too. Keep a visible focus indicator, and never remove an outline without replacing it with
something at least as clear. A user who tabbed in must be able to tab out.

```css
/* PASS: a replacement indicator that is easier to see than the default */
:focus-visible {
  outline: 3px solid var(--color-focus-ring);
  outline-offset: 2px;
}
```

```css
/* FAIL: focus becomes invisible, and keyboard users lose their place */
:focus {
  outline: none;
}
```

A dialog is where focus management is most often wrong. Opening it moves focus in, Tab stays inside while it is open,
Escape closes it, and closing returns focus to the control that opened it.

```javascript
// PASS: move focus in, trap it, restore it on close
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'

export function openDialog(dialog, trigger) {
  const previouslyFocused = trigger ?? document.activeElement

  const items = () => Array.from(dialog.querySelectorAll(FOCUSABLE))

  function onKeydown(event) {
    if (event.key === 'Escape') {
      closeDialog()
      return
    }
    if (event.key !== 'Tab') return

    const focusable = items()
    if (focusable.length === 0) {
      event.preventDefault()
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function closeDialog() {
    dialog.removeEventListener('keydown', onKeydown)
    dialog.hidden = true
    previouslyFocused?.focus()
  }

  dialog.hidden = false
  dialog.addEventListener('keydown', onKeydown)
  ;(items()[0] ?? dialog).focus()

  return closeDialog
}
```

```html
<!-- PASS: the dialog is labelled, modal, and programmatically focusable -->
<div id="confirm" role="dialog" aria-modal="true" aria-labelledby="confirm-title" tabindex="-1" hidden>
  <h2 id="confirm-title">Delete this project</h2>
  <button type="button" data-close>Cancel</button>
  <button type="button" data-confirm>Delete</button>
</div>
```

```html
<!-- FAIL: focus stays behind the overlay, Escape does nothing, nothing names the dialog -->
<div class="modal">
  <p>Delete this project</p>
  <button type="button">Delete</button>
</div>
```

The native `dialog` element with `showModal()` provides the trap, the Escape handling, and the inert background for
free. Prefer it, and hand-roll the trap only when you cannot use it.

Also move focus on a client-side route change, to the new content or to a status region, or a screen-reader user is
left announcing the old page.

---

### Perceivable content

Meet contrast minimums: 4.5:1 for normal text, 3:1 for large text and for meaningful user-interface and graphical
boundaries, including the focus indicator. Never use colour as the only way to convey meaning. Pair it with text, a
shape, or an icon.

```html
<!-- PASS: the state is readable without seeing the colour -->
<p class="status status--error"><span aria-hidden="true">✕</span> Payment failed</p>
```

```html
<!-- FAIL: red is the only signal, invisible to a colour-blind or monochrome reader -->
<p style="color: #dc2626">Payment failed</p>
```

Give every meaningful image a text alternative that conveys its purpose, and mark a purely decorative image with an
empty alt so assistive tech skips it.

```html
<!-- PASS -->
<img src="/chart.png" alt="Revenue grew from 1.2M to 3.4M between 2024 and 2026" />
<img src="/flourish.svg" alt="" />
```

```html
<!-- FAIL: a filename read aloud, and a decorative image announced as content -->
<img src="/chart.png" alt="chart.png" />
<img src="/flourish.svg" alt="decorative swirl graphic" />
```

Respect the reduced-motion preference by gating non-essential animation behind `prefers-reduced-motion`.

```css
/* PASS */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

```css
/* FAIL: parallax and movement regardless of the setting */
.hero { animation: float 4s ease-in-out infinite; }
```

Make targets large enough to hit. WCAG 2.2 AA sets a 24 by 24 CSS pixel minimum, and 44 by 44 is the comfortable
figure to design toward. On an icon-only control, add padding to reach the size rather than enlarging the icon.

---

### Forms

Associate a real label with every form control. Placeholder text is not a label: it disappears on input and many
screen readers do not announce it. Tie an error message to its field programmatically so a screen-reader user learns
what failed and why, not just that something did. Group related controls in a `fieldset` with a `legend`.

```html
<!-- PASS: labelled, marked invalid, and pointing at its own error text -->
<label for="email">Email address</label>
<input
  id="email"
  name="email"
  type="email"
  autocomplete="email"
  aria-invalid="true"
  aria-describedby="email-hint email-error"
/>
<p id="email-hint">We use this for receipts only.</p>
<p id="email-error" role="alert">Enter an email address in the format name@example.com.</p>
```

```html
<!-- FAIL: placeholder as label, error unlinked and colour-only -->
<input type="email" placeholder="Email address" class="input--error" />
<p class="error-text">Invalid</p>
```

`aria-describedby` accepts several ids, so hint text and error text can both be announced. Point at the error element
only while the error is present, keep `aria-invalid` in step with it, and write a message that says how to fix the
problem rather than that something is wrong.

---

### Internationalisation and testing

Build translation-ready from the start: route user-facing text through one localisation layer, set the document
language, and do not bake text into images. Use CSS logical properties so a right-to-left locale does not need a
second stylesheet.

```html
<!-- PASS: the language is declared, so screen readers pick the right voice -->
<html lang="pl">
```

```css
/* PASS: mirrors automatically under dir="rtl" */
.card { padding-inline-start: 16px; }

/* FAIL: pinned to the left in every locale */
.card { padding-left: 16px; }
```

Automated scanners catch only a fraction of real barriers. Test the keyboard path end to end and listen to the flow
with a screen reader before calling anything accessible.

---

### Related skills

- `frontend-design` for the visual direction the palette and type scale express.
- `design-system` for where colour, spacing, and focus-ring tokens live.
- `frontend-patterns` for the React mechanics of keyboard handling and focus management.
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
