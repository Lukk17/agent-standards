### AI UI/UX and Frontend Styling Standards

---

### Core Execution Directives

- Treat all LLM generated UI/UX designs, CSS layouts, and accessibility features as potentially non-compliant or hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every styling and UX decision.
- Append a Zero-Trust directive demanding mandatory web searches for current WCAG 2.2 guidelines and Tailwind/SCSS documentation.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every contrast ratio, ARIA attribute, and configuration detail provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### User Experience UX and Accessibility WCAG 2.2

- Mandate WCAG 2.2 Level AA compliance for all generated UI components. [Confidence: 100%]
  - Link: https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Understanding_WCAG/Perceivable/Color_contrast
  - Quote: "contrast"
- Enforce strict color contrast ratios: a minimum of 4.5:1 for standard text, and 3:1 for large text over 18pt and active user interface components like buttons, icons, input borders. [Confidence: 100%]
- Require explicit definition of interaction states. Every interactive component must define styles for default, hover, focus-visible, active, and disabled states. [Confidence: 100%]
- Ensure keyboard navigability. Never remove focus rings without providing a highly visible fallback using focus-visible. [Confidence: 100%]
- Provide programmatic context for screen readers using appropriate aria attributes like aria-expanded, aria-describedby, or aria-hidden for decorative icons. [Confidence: 100%]

---

### User Interface UI Design Systems

- Enforce a strict 8pt modular grid system, or 4pt for micro-adjustments. All margins, paddings, and heights must scale on this baseline like 8px, 16px, 24px, 32px to ensure visual rhythm. [Confidence: 100%]
  - Link: https://dribbble.com/shots/24375776-Crypto-App-Design-Crypto-Mobile-App-Crypto-Web-App-UI-UX
  - Quote: "defines"
- Use a standardized typography scale based on relative units like rem rather than absolute pixels like px to allow the UI to scale with user browser preferences. Limit font weights to a maximum of three like 400, 500, 700. [Confidence: 100%]
- Enforce Semantic Color Palettes. Never hardcode arbitrary hex values into component files. Map colors to semantic variables like primary, secondary, success, warning, danger, and surface. [Confidence: 100%]
- Implement Defensive UI logic. Require confirmation dialogs or undo toast notifications for destructive actions to prevent accidental data loss. [Confidence: 100%]

---

### Tailwind CSS v4 Architecture

- Strictly enforce Tailwind CSS v4 syntax using the CSS-first approach. Do not generate or modify tailwind.config.js files; use the @theme directive directly within the main CSS file. [Confidence: 100%]
  - Link: https://mcpmarket.com/tools/skills/tailwind-css-v4-best-practices-2
  - Quote: "provides"
- Replace legacy @tailwind directives like base, components, utilities with a single @import "tailwindcss" statement. [Confidence: 100%]
- Abstract repeated UI patterns into framework components rather than relying exclusively on long utility class strings in the HTML template. Use tools like Class Variance Authority or tailwind-variants for complex component state management. [Confidence: 100%]
- Apply the exclamation modifier at the end of classes instead of the legacy prefix modifier. [Confidence: 100%]

---

### SCSS Architecture Pattern

- Mandate the 7-1 architecture pattern for any raw SCSS project to ensure separation of concerns. Break files into 7 specific subdirectories imported into a single main.scss file. [Confidence: 100%]
  - Link: https://pjmcdermott92.medium.com/the-7-1-scss-architecture-430c50b1f35a
  - Quote: "accomplish"
- Enforce the following exact directory structure: base/, components/, layout/, pages/, themes/, abstracts/, and vendors/. [Confidence: 100%]
- Ensure the abstracts/ folder contains only variables, functions, mixins, and placeholders. It must never output a single line of compiled CSS on its own. [Confidence: 100%]
- Prevent nesting deeper than three levels in SCSS to avoid specificity wars and bloated compiled CSS. Use the Block Element Modifier naming convention for vanilla CSS or SCSS components to ensure flat specificity trees. [Confidence: 100%]