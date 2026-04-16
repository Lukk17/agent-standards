### AI UI/UX and Frontend Styling Standards

> **Scope**: UX principles, accessibility, design systems, and high-level styling decisions. For raw CSS/SCSS architecture and Tailwind syntax rules, see `coding/css-standards.md`.

---

### Core Execution Directives

- Treat all LLM generated UI/UX designs, CSS layouts, and accessibility features as potentially non-compliant or hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every styling and UX decision.
- Append a Zero-Trust directive demanding mandatory web searches for current WCAG 2.2 guidelines and Tailwind/SCSS documentation.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every contrast ratio, ARIA attribute, and configuration detail provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### User Experience (UX) and Accessibility — WCAG 2.2

- Mandate WCAG 2.2 Level AA compliance for all generated UI components. [Confidence: 100%]
  - Link: https://www.w3.org/TR/WCAG22/
  - Quote: "perceivable"
- Enforce strict color contrast ratios: a minimum of 4.5:1 for standard text, and 3:1 for large text over 18pt and active user interface components like buttons, icons, and input borders. [Confidence: 100%]
  - Link: https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Perceivable/Color_contrast
- Require explicit definition of interaction states. Every interactive component must define styles for default, hover, focus-visible, active, and disabled states. [Confidence: 100%]
- Ensure keyboard navigability. Never remove focus rings without providing a highly visible fallback using focus-visible. [Confidence: 100%]
- Provide programmatic context for screen readers using appropriate aria attributes like aria-expanded, aria-describedby, or aria-hidden for decorative icons. [Confidence: 100%]
- Enforce a minimum touch target size of **44×44 CSS pixels** for all interactive elements per WCAG 2.5.8 (Target Size Minimum). [Confidence: 100%]
  - Link: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

---

### User Interface (UI) Design Systems

- Enforce a strict **8pt modular grid system**, or 4pt for micro-adjustments. All margins, paddings, and heights must scale on this baseline (8px, 16px, 24px, 32px) to ensure visual rhythm. [Confidence: 100%]
  - Link: https://spec.fm/specifics/8-pt-grid
  - Quote: "8pt"
- Use a standardized typography scale based on relative units like `rem` rather than absolute pixels to allow the UI to scale with user browser preferences. Limit font weights to a maximum of three (e.g., 400, 500, 700). [Confidence: 100%]
- Enforce Semantic Color Palettes. Never hardcode arbitrary hex values into component files. Map colors to semantic variables like `primary`, `secondary`, `success`, `warning`, `danger`, and `surface`. [Confidence: 100%]
- Implement Defensive UI logic. Require confirmation dialogs or undo toast notifications for destructive actions to prevent accidental data loss. [Confidence: 100%]

---

### Responsive Design

- Apply a **mobile-first** design strategy: design for the smallest viewport first and enhance progressively for larger screens. [Confidence: 100%]
- Use standard breakpoints consistently across the project (align with the breakpoints defined in `coding/css-standards.md`).
- Test every UI component at all breakpoints (mobile 375px, tablet 768px, desktop 1280px, wide 1536px) before considering it complete.
- Never use fixed-width pixel layouts for containers that hold variable-length content or need to support internationalisation.

---

### Dark Mode

- Design all components with both light and dark themes from the start; retrofitting dark mode is costly.
- Use semantic color tokens (e.g., `--color-surface`, `--color-on-surface`) that automatically resolve to the correct value for the active theme.
- Ensure contrast ratios are validated for **both** light and dark modes independently.

---

### Motion and Animation

- Respect `prefers-reduced-motion` on all transitions and animations; provide a zero-duration fallback. [Confidence: 100%]
  - Link: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
- Use animations purposefully: they must communicate state change, guide attention, or provide feedback — never decorative only.
- Keep UI transition durations in the range of 100–300ms for micro-interactions; 300–500ms for page-level transitions.

---

### Loading States

- Every data-fetching component must have an explicit loading state (skeleton screen preferred over spinners for layout-heavy content). [Confidence: 100%]
- Skeleton screens must match the approximate shape of the content they replace to prevent layout shift.
- Loading indicators must be accessible: use `aria-busy="true"` on the container and `aria-live="polite"` on status messages.
- Never block the entire viewport with a full-screen spinner for background operations; use inline or section-level indicators.

---

### Error States

- Every form, data table, and async component must have a defined error state with a user-actionable message. [Confidence: 100%]
- Error messages must: explain what went wrong, tell the user what to do next, and avoid technical jargon.
- Distinguish between recoverable errors (retry button) and fatal errors (contact support / navigate away).
- Never silently swallow errors and show an empty state; always distinguish between "empty" and "failed to load".

---

### Form Validation UX

- Validate on **blur** for individual fields (immediate feedback after leaving a field). [Confidence: 100%]
- Re-validate on **submit** for the full form; scroll to and focus the first invalid field automatically.
- Display error messages inline, directly below the affected field, not in a banner at the top of the form.
- Use `aria-describedby` to associate each error message with its input so screen readers announce the error when the field receives focus.
- Never disable the submit button to prevent submission; allow submission and report validation errors instead (disabled buttons cannot receive focus and are inaccessible).

---

### Internationalisation (i18n)

- Design layouts to handle text expansion of up to **40% longer** than English for European languages (e.g., German, Finnish).
- Design layouts to handle **right-to-left (RTL)** text direction for Arabic, Hebrew, and Persian locales using CSS logical properties.
- Never truncate translated strings without an accessible `title` or `aria-label` fallback providing the full text.
- Do not hardcode date, time, number, or currency formats; always use locale-aware formatting (Intl API, date-fns, or equivalent).

---

### SCSS Architecture Pattern

> See `coding/css-standards.md` for the full SCSS 7-1 architecture rules. Summary:

- Mandate the 7-1 architecture pattern: base/, components/, layout/, pages/, themes/, abstracts/, vendors/. [Confidence: 100%]
- Ensure the abstracts/ folder never outputs compiled CSS on its own. [Confidence: 100%]
- Prevent SCSS nesting deeper than three levels; use BEM for flat specificity. [Confidence: 100%]

---

### Tailwind CSS v4 Architecture

> See `coding/css-standards.md` for the full Tailwind v4 rules. Summary:

- Use `@import "tailwindcss"` instead of legacy `@tailwind` directives. [Confidence: 100%]
- Define the design system via `@theme` in the main CSS file; no `tailwind.config.js`. [Confidence: 100%]
- Abstract repeated patterns into `@layer components` classes; do not duplicate long utility strings. [Confidence: 100%]