# Scope

Companion reference for the [angular](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Building or reviewing any Angular component, service, guard, interceptor, or form.
- The user says "build this Angular component", "replace this BehaviorSubject with a signal", "my subscription leaks", "write a functional auth guard", or "add an HTTP error interceptor".
- Choosing between a signal and an observable for a piece of state.
- Fixing a subscription leak or a change-detection performance problem.
- Migrating NgModules to standalone components, or class-based guards and interceptors to functional ones.
- Setting up global error handling, HTTP plumbing, or route-level data loading.
- Writing the Vitest unit and component tests for any of the above.

---

### When not to activate

- React, Next.js, and framework-agnostic web patterns. Use `react-patterns`.
- Next.js rendering and routing. Use `nextjs-app-router-patterns`.
- Visual direction and composition. Use `frontend-design`.
- Tokens, theming, and stylesheet architecture. Use `design-system`.
- WCAG conformance, ARIA, and screen-reader behaviour. Use `web-accessibility`.
- The cross-language engineering baseline of SOLID, naming, and error handling. Use `coding-standards`.

---

### Related skills

- `react-patterns` for React and framework-agnostic web patterns.
- `frontend-design` for visual direction and composition.
- `design-system` for tokens, theming, and stylesheet architecture.
- `web-accessibility` for keyboard, focus, ARIA, and contrast requirements in Angular templates.
- `coding-standards` for the cross-language engineering baseline.
- `e2e-testing` for the Playwright suite that drives the application.
- `api-design` for the contracts the data services call.
