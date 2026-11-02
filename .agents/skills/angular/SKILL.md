---
name: angular
description: "Angular 22 application standards, covering standalone components, signals and RxJS interop, inject(), OnPush change detection, functional guards and interceptors, typed reactive forms, global error handling and Vitest tests. Use when the user says \"build this Angular component\" or \"my subscription leaks\". Not for React and Next.js work, use `react-patterns`."
license: Apache-2.0
---

# Angular Standards

Architecture and code standards for Angular applications: how components are declared, how state flows, how dependencies arrive, and how errors are handled. Every rule here has a modern form and a legacy form, and the legacy form is the one to remove on sight.

Written for Angular 22. Standalone components, signals, RxJS interop, `inject()`, functional guards and interceptors, and typed reactive forms are all stable, so nothing below is gated behind a flag.

---

### When to activate

- Building or reviewing any Angular component, service, guard, interceptor, or form.
- The user says "build this Angular component", "replace this BehaviorSubject with a signal", "my subscription leaks", "write a functional auth guard", or "add an HTTP error interceptor".
- Choosing between a signal and an observable for a piece of state.
- Fixing a subscription leak or a change-detection performance problem.
- Migrating NgModules to standalone components, or class-based guards and interceptors to functional ones.
- Setting up global error handling, HTTP plumbing, or route-level data loading.

---

### When not to activate

- React, Next.js, and framework-agnostic web patterns. Use `react-patterns`.
- Next.js rendering and routing. Use `nextjs-app-router-patterns`.
- Visual direction and composition. Use `frontend-design`.
- Tokens, theming, and stylesheet architecture. Use `design-system`.
- WCAG conformance, ARIA, and screen-reader behaviour. Use `web-accessibility`.
- The cross-language engineering baseline of SOLID, naming, and error handling. Use `coding-standards`.

---

### Reference map

| Task | Open |
| --- | --- |
| A hub rule needs its Pass and Fail example or its full reasoning | [references/core-rules.md](references/core-rules.md) |
| Functional guards and resolvers, HTTP interceptors, typed forms | [references/routing-http-and-forms.md](references/routing-http-and-forms.md) |
| Unit tests, component tests, HTTP mocking, end-to-end setup | [references/testing.md](references/testing.md) |
| Sanitisation, CSP, and internationalisation | [references/security-and-i18n.md](references/security-and-i18n.md) |

---

### Rules

1. Declare components standalone, importing what they use. An NgModule exists only to integrate with legacy code that requires one.
2. Hold synchronous UI state in signals with `computed` for derived values, and keep RxJS for async streams, timing and cancellation. Render an observable with `toSignal` or the `async` pipe, never a `subscribe` that assigns a field.
3. End every component subscription with `takeUntilDestroyed()`, or `takeUntilDestroyed(this.destroyRef)` outside an injection context, never a destroy subject.
4. Choose the mapping operator on purpose: `switchMap` to supersede, `concatMap` to keep order, `exhaustMap` to ignore a second submit, `mergeMap` only for wanted concurrency.
5. Inject with `inject()` into readonly fields, register singletons with `providedIn: 'root'`, and keep `HttpClient` in a data service, never a component.
6. Write guards, resolvers and interceptors as functions, register interceptors in run order with `provideHttpClient(withInterceptors([...]))`, and type every reactive form.
7. Register a custom `ErrorHandler` that logs with context and shows a fallback, and never let `catchError` discard an error unlogged.
8. Run `OnPush`, the default from Angular 22 and set explicitly on an older project, and never bind a template to a method call.
9. Defer heavy sections with `@defer`. Keep constructors to injection-context wiring such as `takeUntilDestroyed()`, `toSignal` and `effect`, with other initialisation in `ngOnInit`.
10. Name files by the style guide, hyphenated and matching the exported class, such as `user-profile.ts`. Keep a `.component.ts` suffix only where the project already uses it throughout.

---

### Doc Comments

Doc comments follow the Doc Comments rules in `coding-standards`, whose TSDoc examples already cover TypeScript. Angular delta: an `Observable` return is non-obvious by nature, so `@returns` says whether it completes, replays, or has to be unsubscribed, for example `@returns a cold Observable that completes after one emission`.

---

### Related skills

- `react-patterns` for React and framework-agnostic web patterns.
- `frontend-design` for visual direction and composition.
- `design-system` for tokens, theming, and stylesheet architecture.
- `web-accessibility` for keyboard, focus, ARIA, and contrast requirements in Angular templates.
- `coding-standards` for the cross-language engineering baseline.
- `e2e-testing` for the Playwright suite that drives the application.
- `api-design` for the contracts the data services call.

---

### Checklist

- Every new component is standalone and runs `OnPush`, the default from Angular 22, set explicitly only on an older project. `ChangeDetectionStrategy.Eager` carries a justification.
- Synchronous UI state lives in signals, and no `BehaviorSubject` is used as a state container.
- Every component-level subscription ends with `takeUntilDestroyed`, and no `ngOnDestroy` destroy subject remains.
- No `subscribe` call in a component assigns a field that a signal or the `async` pipe could hold.
- Dependencies arrive through `inject()`, and no component injects `HttpClient` directly.
- Guards, resolvers, and interceptors are functions, not classes.
- Every reactive form is typed, and no untyped form variant remains.
- A custom `ErrorHandler` is registered, and no `catchError` discards an error without logging it.
- No template binds to a method call.
- Doc comments follow `coding-standards`, and every `Observable` return says whether it completes, replays, or must be unsubscribed.
