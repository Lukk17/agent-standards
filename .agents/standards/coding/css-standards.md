### AI CSS and SCSS Development Standards

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

---

### Tailwind CSS v4 Architecture

- Strictly enforce Tailwind CSS v4 syntax. Do not generate or modify tailwind.config.js files, as v4 is strictly CSS-first using the @theme directive. [Confidence: 100%]
  - Link: https://tailwindcss.com/blog/tailwindcss-v4
  - Quote: "an"
- Replace legacy @tailwind base, components, and utilities directives with a single @import "tailwindcss" statement. [Confidence: 100%]
- Utilize modern CSS color functions and variables rather than legacy opacity classes. Use bg-red-500/50 instead of chaining bg-red-500 and bg-opacity-50. [Confidence: 100%]
- Apply the exclamation modifier at the end of classes instead of the legacy prefix modifier. [Confidence: 100%]