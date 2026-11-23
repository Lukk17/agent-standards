# Tailwind CSS

The design-system rules as they apply in a project that uses Tailwind CSS. Open it when the project has Tailwind in it, or is moving a Tailwind v3 configuration to the v4 CSS-first setup.

Written for Tailwind CSS v4, which is configured in CSS through `@theme` and no longer auto-detects `tailwind.config.js`.

---

### Configure Tailwind v4 in CSS

Tailwind v4 no longer auto-detects `tailwind.config.js`. A project may still load one with the `@config` directive, so search the stylesheets for `@config` before treating a config file as dead. The [upgrade guide](https://tailwindcss.com/docs/upgrade-guide) says "JavaScript config files are still supported for backward compatibility, but they are no longer detected automatically in v4". New configuration lives in the `@theme` block, and every token defined there becomes both a CSS custom property and a Tailwind utility.

```css
/* PASS: styles/main.css, one source for the theme */
@import "tailwindcss";

@theme {
  --color-primary: #2563eb;
  --color-primary-foreground: #ffffff;
  --font-sans: "Inter Variable", sans-serif;
  --radius-md: 0.5rem;
  --spacing-18: 4.5rem;
}

@layer components {
  .btn-primary {
    @apply bg-(--color-primary) text-(color:--color-primary-foreground) rounded-(--radius-md) px-4 py-2;
  }
}
```

```javascript
// FAIL: a v3 config file that Tailwind v4 does not read
module.exports = {
  theme: { extend: { colors: { primary: '#2563eb' } } },
}
```

---

### Keep arbitrary values out of themed surfaces

Dark mode works by overriding semantic tokens per theme, as [modes-and-tokens.md](modes-and-tokens.md) shows. An arbitrary value in a class carries a raw colour past every theme.

```tsx
// FAIL: an arbitrary value that no theme can override
<div className="bg-[#ffffff] text-[#111827]" />
```

---

### Generate mode in a Tailwind project

Generate mode scans the Tailwind classes in the markup for the values already in use, beside the CSS.
