---
name: react-patterns
description: 'React 19 patterns for composition, hooks, async state, data fetching, forms and animation. Use when the user says "build a React component" or "write a custom hook". Not for Next.js, use `nextjs-app-router-patterns`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# React Development Patterns

React patterns for maintainable, performant user interfaces, covering composition, hooks, async state, data access, performance, forms, and animation. Everything here is framework-agnostic React that works the same inside or outside a meta-framework.

Written for React 19 with TypeScript and React Compiler. Server Components, streaming, and route-level caching belong to `nextjs-app-router-patterns`, and this skill defers to it on all three.

---

### When not to activate

- Server Components, streaming, route caching, Server Actions and route handlers, use `nextjs-app-router-patterns`.
- WCAG conformance, ARIA semantics and screen-reader behaviour, use `web-accessibility`.
- Profiling and Core Web Vitals work beyond React-level fixes, use `performance-optimization`.

---

### Rules

1. Declare components as named function declarations for hoisting and consistency, and keep arrow functions for callbacks and inline handlers.
2. Compose small pieces rather than inheriting or growing a flag surface. Error boundaries are the one class component, and compound components share state through a parent context.
3. Model async state as one discriminated union that callers switch on by `status`, never separate data, loading and error flags.
4. Route every network call through one typed API client that owns the base URL, headers, auth and response types. No `fetch` in a component.
5. With React Compiler on, hand-write no `useMemo`, `useCallback` or `React.memo` except as a stated escape hatch, and leave existing memoisation until a test proves removal safe. Without it, memoise only what you measured.
6. Copy before `sort`, `splice` or `reverse`, because they mutate a prop or state in place.
7. Lazy load heavy client modules behind `Suspense`, and virtualise long lists.
8. Send every user-facing string through the i18n layer by key, metadata titles, labels and toasts included, with a catalogue per supported locale. Identifiers and keys are English, no component holds a locale literal such as `"pl"` because one i18n config module owns the locales, and an AST guard fails lint on new hard-coded copy.
9. Every animation respects `prefers-reduced-motion`.
10. Doc comments follow the Doc Comments rules in `coding-standards`, plus: a prop is documented on its field in the props type, never as a `@param` on the component, and a hook documents its return only when it is non-obvious.

---

### Reference map

| Task | Open |
| --- | --- |
| A rule above needs its Pass and Fail example, its full reasoning or the doc comment delta | [references/core-rules.md](references/core-rules.md) |
| Context and reducer stores, custom state hooks, debouncing | [references/state-management.md](references/state-management.md) |
| The typed API client, async data hooks, render props loaders, code splitting, virtualisation | [references/data-fetching.md](references/data-fetching.md) |
| Controlled forms, validation, error boundaries, i18n wiring | [references/forms.md](references/forms.md) |
| Animation with `motion/react`, reduced motion, timing budgets | [references/animation.md](references/animation.md) |
| Keyboard navigation and focus management in React | [references/accessibility.md](references/accessibility.md) |
| Before calling a React change or a React review done | [references/checklist.md](references/checklist.md) |
