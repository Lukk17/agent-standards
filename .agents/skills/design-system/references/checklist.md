# Design System Checklist

Run it before calling a token set, an audit or a styling change done. The item that names Tailwind applies where the project uses Tailwind, and the item that names `main.scss` where it uses Sass.

- No hex value, font stack, radius, shadow, or spacing number appears outside the token files.
- Every token name describes a role, and no name contains a value or a raw pixel count.
- Spacing, sizing, and gaps are multiples of 8px, with 4px reserved for micro-adjustments.
- Tailwind configuration lives in `@theme`, and no `tailwind.config.js` remains.
- Stylesheets follow the 7-1 layout, `abstracts/` emits no CSS, and `main.scss` only imports.
- Dark mode is driven by semantic token overrides, and both themes have been viewed.
- Media queries are `min-width` only, from one shared breakpoint set.
- An audit finding names a file and a line, and a slop-check finding names the token it bypasses.
- Colour choices have been checked against the contrast rules in `web-accessibility`.
