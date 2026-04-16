### AI CSS and SCSS Development Standards

> **Scope**: Raw CSS and SCSS architecture rules. Tailwind-specific rules live here as well. For UX, accessibility, and design system standards (spacing grids, typography, colour palettes, WCAG), see `ui-ux-styling-standards.md`.

---

### Core Execution Directives

- Treat all LLM generated CSS, SCSS architecture, and selector logic as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every styling decision.
- Append a Zero-Trust directive demanding mandatory web searches for current SCSS architecture best practices and CSS module specs.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every configuration detail and architecture rule provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### SCSS Architecture Pattern

- Mandate the 7-1 architecture pattern for any raw SCSS project to ensure separation of concerns. Break files into 7 specific subdirectories imported into a single main.scss file. [Confidence: 100%]
  - Link: https://pjmcdermott92.medium.com/the-7-1-scss-architecture-430c50b1f35a
  - Quote: "accomplish"
- Enforce the following exact directory structure: base/, components/, layout/, pages/, themes/, abstracts/, and vendors/. [Confidence: 100%]
- Ensure the abstracts/ folder contains only variables, functions, mixins, and placeholders. It must never output a single line of compiled CSS on its own. [Confidence: 100%]

---

### Nesting and Specificity

- Prevent nesting deeper than three levels in SCSS to avoid specificity wars and bloated compiled CSS. [Confidence: 100%]
- Use the BEM (Block Element Modifier) naming convention for vanilla CSS or SCSS components to ensure flat specificity trees. [Confidence: 100%]
- Never use `!important` except as a last resort to override third-party library styles; document the reason with a comment. [Confidence: 100%]

---

### CSS Custom Properties (Variables)

- Define all design tokens (colours, spacing, typography, radii) as CSS custom properties on `:root`, not as SCSS variables, so they are accessible to JavaScript and overridable in themes. [Confidence: 100%]
- Follow a `--category-name-variant` naming convention: `--color-primary-500`, `--spacing-4`, `--radius-md`. [Confidence: 100%]
- Use SCSS variables (`$`) only for SCSS-internal values (breakpoints, compile-time math); use CSS custom properties for runtime-accessible values. [Confidence: 100%]

---

### Responsive Design

- Use a **mobile-first** approach: write base styles for the smallest viewport and progressively enhance with `min-width` media queries. [Confidence: 100%]
- Define standard breakpoints as CSS custom properties or SCSS variables in `abstracts/_breakpoints.scss`:
  ```scss
  $bp-sm:  640px;
  $bp-md:  768px;
  $bp-lg:  1024px;
  $bp-xl:  1280px;
  $bp-2xl: 1536px;
  ```
- Prefer **CSS container queries** (`@container`) over viewport media queries for component-level responsiveness where browser support allows. [Confidence: 100%]

---

### Dark Mode

- Implement dark mode using CSS custom property overrides inside a `prefers-color-scheme: dark` media query and/or a `.dark` class on the `<html>` element for JS-controlled toggling. [Confidence: 100%]
  ```css
  :root { --color-bg: #ffffff; --color-text: #111111; }
  @media (prefers-color-scheme: dark) {
    :root { --color-bg: #111111; --color-text: #f5f5f5; }
  }
  ```
- Never hardcode light-mode colour values in component files; always reference semantic custom properties. [Confidence: 100%]

---

### Motion and Animation

- Respect the `prefers-reduced-motion` media query on **all** transitions and animations. [Confidence: 100%]
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
  ```
- Animate only GPU-composited properties (`transform`, `opacity`) for smooth 60 fps performance; avoid animating `width`, `height`, `top`, `left`, or any property that triggers layout. [Confidence: 100%]
- Use `will-change: transform` sparingly and only on elements that are actively animating; remove it after the animation completes. [Confidence: 100%]

---

### Performance

- Extract **critical CSS** (above-the-fold styles) and inline it in the `<head>` to eliminate render-blocking stylesheet requests on initial page load.
- Use **CSS logical properties** (`inline-start`, `block-end`) instead of physical properties (`left`, `bottom`) to natively support RTL layouts without extra overrides. [Confidence: 100%]
- Avoid deeply descendant selectors (e.g., `.card ul li a span`); they are slow and brittle. BEM naming eliminates the need for them.

---

### Tailwind CSS v4 Architecture

- Strictly enforce Tailwind CSS v4 syntax. Do not generate or modify tailwind.config.js files, as v4 is strictly CSS-first using the @theme directive. [Confidence: 100%]
  - Link: https://tailwindcss.com/blog/tailwindcss-v4
  - Quote: "an"
- Replace legacy @tailwind base, components, and utilities directives with a single @import "tailwindcss" statement. [Confidence: 100%]
- Utilize modern CSS color functions and variables rather than legacy opacity classes. Use bg-red-500/50 instead of chaining bg-red-500 and bg-opacity-50. [Confidence: 100%]
- Apply the exclamation modifier at the end of classes instead of the legacy prefix modifier. [Confidence: 100%]
- Abstract repeated utility patterns into component classes using `@layer components { }` rather than duplicating long class strings across templates.