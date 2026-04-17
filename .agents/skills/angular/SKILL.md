---
name: angular
description: Angular-specific standards for project structure, standalone components, signals, routing, testing, and performance.
origin: project-standards
---

# Angular Standards

## Core Execution Directives

- Treat all LLM generated Angular components, services, RxJS pipelines, and RxJS operators as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every Angular architectural decision.
- Append a Zero-Trust directive demanding mandatory web searches for current Angular documentation, specifically regarding Signals and RxJS interop.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official Angular documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every Angular API, RxJS operator, and configuration detail provided.
- Mandate direct, working links to the official Angular documentation used to ground the code.

---

## Modern Architecture and Signals

- Default to using Standalone Components. Do not generate NgModules unless strictly required for legacy integration.
- Use Angular Signals for synchronous state management and UI reactivity instead of `BehaviorSubject` where possible.
- Use the `toSignal` function from the `@angular/core/rxjs-interop` package to track the value of an Observable in the template.
  - Ref: https://angular.dev/ecosystem/rxjs-interop

---

## RxJS Patterns and State Management

- Use RxJS strictly for asynchronous streams, event handling, and complex timing operations.
- Prevent memory leaks by mandating the `takeUntilDestroyed` operator from `@angular/core/rxjs-interop` for all component-level subscriptions. Do not use the legacy `Subject` and `ngOnDestroy` pattern.
  - Ref: https://angular.dev/ecosystem/rxjs-interop/take-until-destroyed
- Enforce the use of the `async` pipe in templates for any raw Observables that are not converted to Signals, preventing manual `subscribe` calls in the component class.
- Structure complex RxJS pipelines using higher-order mapping operators like `switchMap` for HTTP requests and `concatMap` for ordered operations to avoid race conditions.

---

## Dependency Injection

- Mandate the use of the `inject` function for dependency injection instead of constructor injection. This aligns with modern functional patterns and simplifies component inheritance.
- Register singleton services using the `providedIn: 'root'` syntax inside the `@Injectable` decorator to ensure tree-shaking works correctly.
- Do not inject the `HttpClient` directly into components. Abstract all API communication into dedicated data services.

---

## Component Lifecycle and Naming Conventions

- Avoid putting complex logic inside the constructor. Defer initialization logic to the `ngOnInit` lifecycle hook.
- Follow the Angular Style Guide naming conventions. Use `feature.type.ts` for file names.
  - Ref: https://angular.dev/style-guide
- Separate file names with dashes, and match the file name to the TypeScript class name.

---

## Performance and Change Detection

- Set `ChangeDetectionStrategy.OnPush` for all newly generated components to optimize rendering performance.
- Do not call functions directly from HTML templates for data binding, as they execute on every change detection cycle. Bind to properties, Signals, or use pure pipes instead.
- Defer loading of heavy components using the `@defer` block syntax available in modern Angular templates.

---

## Testing

- Unit-test components and services using **TestBed** with **Jest** (via `jest-preset-angular`) or **Vitest** as the test runner.
- Use `@testing-library/angular` for component tests; query by accessible roles and labels, not by CSS selectors or component internals.
- Write end-to-end tests with **Playwright** (`@playwright/test`); do not use the deprecated Protractor.
- Mock HTTP calls in unit tests using `provideHttpClientTesting` and `HttpTestingController`; never mock `HttpClient` directly.

---

## Routing Guards and Resolvers

- Implement route guards as functional guards using `inject()` rather than class-based `CanActivate`.
- Use `CanDeactivate` guards for forms with unsaved changes to prevent accidental data loss.
- Use resolvers (`ResolveFn`) only for data that is required before the component can render; for optional or deferred data, fetch inside the component.

---

## Forms

- Use **Reactive Forms** (`FormGroup`, `FormControl`) for all non-trivial forms. Do not use Template-Driven Forms for forms with complex validation or dynamic fields.
- Use **typed forms** (`FormControl<string>`, `FormGroup<{...}>`) introduced in Angular 14+; never use untyped form variants.
- Extract reusable validators into pure functions; never inline complex validation logic in the template or component class.

---

## HTTP Interceptors

- Use functional interceptors (`HttpInterceptorFn`) rather than class-based interceptors.
- Implement a dedicated auth interceptor that attaches the Bearer token to outbound requests; inject the token source with `inject()`.
- Implement a global error-normalisation interceptor that maps HTTP error responses to typed application errors before they reach services.

---

## Global Error Handling

- Provide a custom `ErrorHandler` implementation that captures uncaught errors, logs them with context (URL, user ID), and displays a user-friendly fallback UI instead of a blank screen.
- Never swallow errors in `catchError` without logging them; always re-throw or convert to a typed error signal.

---

## Security

- Never bypass Angular's built-in HTML sanitisation by calling `bypassSecurityTrustHtml` unless the content is generated exclusively server-side and sanitised there.
- Use Angular's `DomSanitizer` API for URL and style binding only when absolutely necessary and document the reason.
- Set a strict Content Security Policy in the server response headers; Angular's template compiler generates CSP-compatible code when `nonce` is configured.

---

## Internationalisation (i18n)

- Use Angular's built-in `@angular/localize` system for static text extraction and locale-specific builds.
- Never hardcode user-visible strings directly in templates or component classes; always use `i18n` attributes or `$localize` tagged templates.
- For runtime language switching without full-page reloads, use `ngx-translate` as a complement to Angular i18n.
