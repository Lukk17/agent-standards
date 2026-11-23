# Sass and the 7-1 Pattern

The stylesheet layout rule in full, for a project that writes its styles in Sass. Open it when laying out a `styles/` folder, or when reviewing where a rule was put.

---

### Organise stylesheets with the 7-1 pattern

Seven folders and one entry file, so a reader knows where a rule lives before opening anything.

```text
styles/
├── abstracts/    Variables, functions, mixins, placeholders
├── base/         Reset, typography, base element styles
├── components/   Component styles, BEM named
├── layout/       Grid, header, footer, sidebar
├── pages/        Page-specific overrides
├── themes/       Light and dark token overrides
├── vendors/      Third-party overrides
└── main.scss     Imports only, no rules of its own
```

```scss
// PASS: abstracts holds logic only, and main.scss only imports
// abstracts/_spacing.scss
@function space($step) { @return $step * 8px; }

// FAIL: abstracts emitting CSS, and a rule written straight into main.scss
// abstracts/_spacing.scss
.container { padding: 16px; }
```

`abstracts/` emits no CSS, `components/` is never imported into `abstracts/`, and component classes follow
`.block__element--modifier`.
