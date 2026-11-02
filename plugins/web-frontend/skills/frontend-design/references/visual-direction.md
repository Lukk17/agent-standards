# Visual Direction

Contents:

- [Commit to one direction before writing CSS](#commit-to-one-direction-before-writing-css)
- [Define the visual system once, in variables](#define-the-visual-system-once-in-variables)
- [Compose with intention, not with a default grid](#compose-with-intention-not-with-a-default-grid)
- [Direct the motion instead of scattering it](#direct-the-motion-instead-of-scattering-it)
- [Choose type with character](#choose-type-with-character)
- [Weight the palette](#weight-the-palette)
- [Give the background atmosphere](#give-the-background-atmosphere)

Companion reference for the [frontend-design](../SKILL.md) skill. Load it for the pass and fail HTML and CSS behind each rule: committing to a direction, the variable system, composition, motion, type, palette and background.

---

### Commit to one direction before writing CSS

Safe-average UI is worse than a coherent aesthetic with a few bold choices. Settle the purpose, the audience, the
emotional tone, the direction, and the one thing the user should remember, then execute that one direction cleanly.
Workable directions include brutally minimal, editorial, industrial, luxury, playful, geometric, retro-futurist, soft
and organic, and maximalist. Do not blend them casually.

```text
PASS: editorial. Serif display at 4rem, tight leading, hairline rules, one ink accent, generous outer margin,
asymmetric two-column body. Every later decision gets checked against that sentence.
```

```text
FAIL: "modern and clean, but also bold and playful, with a professional feel." Four directions, no decisions,
and the result will read as a template.
```

---

### Define the visual system once, in variables

Type hierarchy, colour, spacing rhythm, layout logic, motion rules, and surface treatment get named once and reused.
An interface that grows by inventing values drifts within a week.

```css
/* PASS: named decisions the whole surface reuses */
:root {
  --font-display: "Fraunces", Georgia, serif;
  --font-body: "Inter", system-ui, sans-serif;
  --step-0: 1rem;
  --step-3: clamp(2.5rem, 5vw, 4rem);
  --space-3: 12px;
  --space-8: 64px;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

```css
/* FAIL: values invented per component, nothing shared */
.hero h1 { font-size: 41px; margin-bottom: 27px; }
.card h3 { font-size: 19px; margin-bottom: 13px; }
```

---

### Compose with intention, not with a default grid

Asymmetry sharpens hierarchy, overlap creates depth, and whitespace directs focus. A symmetrical card grid is the
default that happens when nobody decided anything, so reach for it only when the content genuinely is a set of peers.

Here is the same three-item section twice. The first is what generic output looks like: three identical boxes, equal
weight, no entry point for the eye.

```html
<!-- FAIL: three peers, nothing leads, the reader has no route through it -->
<section class="grid">
  <article class="card"><h3>Atlas</h3><p>Logistics dashboard</p></article>
  <article class="card"><h3>Ferrous</h3><p>Steel marketplace</p></article>
  <article class="card"><h3>Quill</h3><p>Editorial platform</p></article>
</section>
```

```css
/* FAIL: the grid is doing the designing */
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.card { padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px; }
```

The second commits to an editorial direction. One item leads at display size, the other two become a numbered index
in a narrower column, and hairline rules replace the boxes. Same content, same component count, one clear route
through it.

```html
<!-- PASS: one lead, a supporting index, an explicit reading order -->
<section class="work">
  <article class="work__lead">
    <p class="work__kicker">Selected work</p>
    <h3>Atlas</h3>
    <p class="work__blurb">A logistics dashboard for freight forwarders moving 40,000 containers a month.</p>
  </article>
  <article class="work__item"><h3>Ferrous</h3><p>Steel marketplace</p></article>
  <article class="work__item"><h3>Quill</h3><p>Editorial platform</p></article>
</section>
```

```css
/* PASS: asymmetric columns, one dominant voice, rules instead of boxes */
.work {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(0, 4fr);
  gap: var(--space-3) var(--space-8);
  align-items: start;
  counter-reset: entry;
}

.work__lead { grid-row: span 2; }

.work__kicker {
  font-size: 0.75rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}

.work__lead h3 {
  font-family: var(--font-display);
  font-size: var(--step-3);
  line-height: 0.95;
  margin: var(--space-3) 0;
}

.work__item {
  counter-increment: entry;
  border-top: 1px solid var(--color-rule);
  padding-top: var(--space-3);
}

.work__item h3::before {
  content: counter(entry, decimal-leading-zero);
  margin-inline-end: var(--space-3);
  color: var(--color-ink-muted);
  font-variant-numeric: tabular-nums;
}
```

Break the grid when the composition benefits, use diagonals, offsets, and grouping deliberately, and keep the reading
flow obvious even when the layout is unconventional.

---

### Direct the motion instead of scattering it

One well-directed load sequence beats twenty random hover effects. Animation should reveal hierarchy, stage
information, reinforce an action, or create one memorable moment. Anything else is decoration that costs frames.

```css
/* PASS: one staged reveal that establishes the hierarchy on entry */
.hero > * { opacity: 0; transform: translateY(12px); animation: rise 600ms var(--ease-out) forwards; }
.hero > :nth-child(2) { animation-delay: 90ms; }
.hero > :nth-child(3) { animation-delay: 180ms; }
```

```css
/* FAIL: every element animating on its own for no reason */
.card:hover { transform: scale(1.04) rotate(1deg); }
.badge { animation: pulse 2s infinite; }
.icon:hover { animation: spin 400ms; }
```

Every animation still has to respect the user's motion preference. See `web-accessibility` for the rule and the
implementation.

---

### Choose type with character

Typeface choice carries more of the direction than any other single decision. Pair a distinctive display face with a
readable body face when the page is design-led, and let the scale do the work instead of weight alone.

```css
/* PASS: a display voice and a working body face, with real scale contrast */
h1 { font-family: var(--font-display); font-size: var(--step-3); line-height: 0.95; letter-spacing: -0.02em; }
p  { font-family: var(--font-body); font-size: var(--step-0); line-height: 1.6; max-width: 62ch; }
```

```css
/* FAIL: one system stack, hierarchy faked with bold */
h1 { font-family: system-ui; font-size: 1.5rem; font-weight: 700; }
p  { font-family: system-ui; font-size: 1rem; }
```

---

### Weight the palette

One dominant field with selective accents reads as designed. Evenly weighted palettes read as a colour picker. Avoid
the purple-to-blue gradient on white unless the product genuinely calls for it.

```css
/* PASS: a dominant ground, one accent that means something */
:root {
  --color-ground: #12100e;
  --color-ink: #f5f1ea;
  --color-ink-muted: #8b857c;
  --color-accent: #e4572e;
}
```

```css
/* FAIL: five accents of equal weight, none of them signals anything */
:root { --blue: #3b82f6; --purple: #a855f7; --pink: #ec4899; --green: #22c55e; --amber: #f59e0b; }
```

Colour is direction here. Where those values live, how they are named, and how they invert for dark mode belong to
`design-system`, and whether they clear contrast minimums belongs to `web-accessibility`.

---

### Give the background atmosphere

A flat empty background is rarely the best answer on a product-facing page. Gradients, meshes, textures, subtle noise,
patterns, and layered transparency all add depth, as long as they stay behind the content rather than competing with
it.

```css
/* PASS: layered ground that stays behind the type */
.hero {
  background:
    radial-gradient(60% 80% at 20% 0%, rgba(228, 87, 46, 0.18), transparent 70%),
    linear-gradient(180deg, #12100e, #1c1916);
}
```

```css
/* FAIL: flat white, or a busy field the text has to fight */
.hero { background: #ffffff; }
```
