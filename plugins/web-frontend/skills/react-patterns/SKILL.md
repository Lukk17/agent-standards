---
name: react-patterns
description: "React 19 patterns for component composition, custom hooks, async state, a typed API client, memoisation under React Compiler, code splitting, virtualisation, forms and animation. Use when the user says \"build a React component\", \"write a custom hook\" or \"this list re-renders on every keystroke\". Not for Next.js rendering, routing and caching, use `nextjs-app-router-patterns`."
license: Apache-2.0
---

# React Development Patterns

React patterns for maintainable, performant user interfaces, covering composition, hooks, async state, data access, performance, forms, and animation. Everything here is framework-agnostic React that works the same inside or outside a meta-framework.

Written for React 19 with TypeScript and React Compiler. Server Components, streaming, and route-level caching belong to `nextjs-app-router-patterns`, and this skill defers to it on all three.

---

### When to activate

- Building React components: composition, props, rendering, compound components.
- The user says "build a React component", "write a custom hook", "this list re-renders on every keystroke", "lazy load this chart", or "animate this list on mount".
- Managing state with `useState`, `useReducer`, Context, or a store such as Zustand.
- Implementing client-side data fetching with SWR, React Query, or a typed API client.
- Optimising rendering: memoisation, virtualisation, code splitting.
- Working with forms: validation, controlled inputs, schema parsing.
- Handling client-side routing and navigation.
- Adding animation to a React interface.

---

### When not to activate

- Server Components, streaming, route caching, Server Actions, route handlers. Use `nextjs-app-router-patterns`.
- Visual direction, typography, composition, and motion direction. Use `frontend-design`.
- Tokens, theming, and stylesheet architecture. Use `design-system`.
- WCAG conformance, ARIA semantics, and screen-reader behaviour. Use `web-accessibility`.
- Angular components, signals, and RxJS. Use `angular`.
- Profiling and Core Web Vitals work beyond React-level fixes. Use `performance-optimization`.

---

### Reference map

| Task | Open |
| --- | --- |
| A hub rule needs its Pass and Fail example or its full reasoning | [references/core-rules.md](references/core-rules.md) |
| Context and reducer stores, custom state hooks, debouncing | [references/state-management.md](references/state-management.md) |
| The typed API client, async data hooks, render props loaders | [references/data-fetching.md](references/data-fetching.md) |
| Controlled forms, validation, error boundaries, i18n wiring | [references/forms.md](references/forms.md) |
| Animation with `motion/react`, reduced motion, timing budgets | [references/animation.md](references/animation.md) |
| Keyboard navigation and focus management in React | [references/accessibility.md](references/accessibility.md) |

---

### Rules

1. Declare components as named function declarations for hoisting and consistency, and keep arrow functions for callbacks and inline handlers.
2. Compose small pieces rather than inheriting or growing a flag surface. Error boundaries are the one class component, and compound components share state through a parent context.
3. Model async state as one discriminated union that callers switch on by `status`, never separate data, loading and error flags.
4. Route every network call through one typed API client that owns the base URL, headers, auth and response types. No `fetch` in a component.
5. With React Compiler on, hand-write no `useMemo`, `useCallback` or `React.memo` except as a stated escape hatch, and leave existing memoisation until a test proves removal safe. Without it, memoise only what you measured.
6. Copy before `sort`, `splice` or `reverse`, because they mutate a prop or state in place.
7. Lazy load heavy client modules behind `Suspense`, and virtualise long lists.
8. Send every user-facing string through the i18n layer by key.

---

### Doc Comments

Doc comments follow the Doc Comments rules in `coding-standards`, whose TSDoc examples already cover TypeScript. React delta: props are the parameters of a component, so a prop that needs a note gets it on its field in the props type, where the editor shows it at every call site, and never as a `@param` on the component function. A hook documents its return only when it is non-obvious, such as `null` until the first message arrives.

---

### Related skills

- `nextjs-app-router-patterns` owns Server Components, streaming, route caching, Server Actions, and route handlers. This skill does not cover them.
- `web-accessibility` owns WCAG conformance, ARIA semantics, and screen-reader behaviour. The React mechanics for keyboard and focus are in [references/accessibility.md](references/accessibility.md), and the requirements are in `web-accessibility`.
- `frontend-design` for visual direction and motion direction.
- `design-system` for tokens, theming, and stylesheet architecture.
- `performance-optimization` for profiling and Core Web Vitals work beyond React-level fixes.
- `e2e-testing` for driving these components in a browser.
- `coding-standards` for the shared engineering floor these patterns sit on.

---

### Checklist

- Every top-level component is a named function declaration, except an error boundary, which React supports only as a class component.
- Component families are composed, not configured through a growing flag surface.
- Every async operation exposes one `AsyncState` union, not separate data, loading, and error flags.
- No component or hook calls `fetch` directly, and every endpoint lives in the typed API client.
- With React Compiler on, a hand-written `useMemo`, `useCallback`, or `React.memo` is an escape hatch with a stated reason. Without it, each traces back to a measurement.
- No sort, splice, or reverse mutates a prop or a state value in place.
- Heavy client-only modules are lazy loaded, and lists past a few hundred rows are virtualised.
- Every user-facing string goes through the i18n layer.
- Every animation respects `prefers-reduced-motion`.
- Doc comments follow `coding-standards`, and a prop is documented on its props type, never as a `@param` on the component.
