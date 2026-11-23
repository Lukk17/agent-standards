# Scope

Companion reference for the [react-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building React components: composition, props, rendering, compound components.
- The user says "build a React component", "write a custom hook", "this list re-renders on every keystroke", "lazy load this chart", or "animate this list on mount".
- Managing state with `useState`, `useReducer`, Context, or a store such as Zustand.
- Implementing client-side data fetching with SWR, React Query, or a typed API client.
- Optimising rendering: memoisation under React Compiler, virtualisation, code splitting.
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

### Related skills

- `nextjs-app-router-patterns` owns Server Components, streaming, route caching, Server Actions, and route handlers. This skill does not cover them.
- `web-accessibility` owns WCAG conformance, ARIA semantics, and screen-reader behaviour. The React mechanics for keyboard and focus are in [references/accessibility.md](accessibility.md), and the requirements are in `web-accessibility`.
- `frontend-design` for visual direction and motion direction.
- `design-system` for tokens, theming, and stylesheet architecture.
- `performance-optimization` for profiling and Core Web Vitals work beyond React-level fixes.
- `e2e-testing` for driving these components in a browser.
- `coding-standards` for the shared engineering floor these patterns sit on.
