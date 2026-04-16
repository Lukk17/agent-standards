### AI Angular Development Standards

---

### Core Execution Directives

- Treat all LLM generated Angular components, services, RxJS pipelines, and RxJS operators as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every Angular architectural decision.
- Append a Zero-Trust directive demanding mandatory web searches for current Angular documentation, specifically regarding Signals and RxJS interop.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official Angular documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every Angular API, RxJS operator, and configuration detail provided.
- Mandate direct, working links to the official Angular documentation used to ground the code.

---

### Modern Architecture and Signals

- Default to using Standalone Components. Do not generate NgModules unless strictly required for legacy integration. [Confidence: 100%]
- Use Angular Signals for synchronous state management and UI reactivity instead of BehaviorSubject where possible. [Confidence: 100%]
- Use the toSignal function from the @angular/core/rxjs-interop package to track the value of an Observable in the template. [Confidence: 100%]
  - Link: https://angular.dev/ecosystem/rxjs-interop
  - Quote: "APIs"

---

### RxJS Patterns and State Management

- Use RxJS strictly for asynchronous streams, event handling, and complex timing operations. [Confidence: 100%]
- Prevent memory leaks by mandating the takeUntilDestroyed operator from @angular/core/rxjs-interop for all component-level subscriptions. Do not use the legacy Subject and ngOnDestroy pattern. [Confidence: 100%]
  - Link: https://angular.dev/ecosystem/rxjs-interop/take-until-destroyed
  - Quote: "@angular/core/rxjs-interop"
- Enforce the use of the async pipe in templates for any raw Observables that are not converted to Signals, preventing manual subscribe calls in the component class. [Confidence: 100%]
- Structure complex RxJS pipelines using higher-order mapping operators like switchMap for HTTP requests and concatMap for ordered operations to avoid race conditions. [Confidence: 100%]

---

### Dependency Injection

- Mandate the use of the inject function for dependency injection instead of constructor injection. This aligns with modern functional patterns and simplifies component inheritance. [Confidence: 100%]
- Register singleton services using the providedIn root syntax inside the @Injectable decorator to ensure tree-shaking works correctly. [Confidence: 100%]
- Do not inject the HttpClient directly into components. Abstract all API communication into dedicated data services. [Confidence: 100%]

---

### Component Lifecycle and Naming Conventions

- Avoid putting complex logic inside the constructor. Defer initialization logic to the ngOnInit lifecycle hook. [Confidence: 100%]
- Follow the Angular Style Guide naming conventions. Use feature.type.ts for file names. [Confidence: 100%]
  - Link: https://angular.dev/style-guide
  - Quote: "range"
- Separate file names with dashes, and match the file name to the TypeScript class name. [Confidence: 100%]

---

### Performance and Change Detection

- Set ChangeDetectionStrategy.OnPush for all newly generated components to optimize rendering performance. [Confidence: 100%]
- Do not call functions directly from HTML templates for data binding, as they execute on every change detection cycle. Bind to properties, Signals, or use pure pipes instead. [Confidence: 100%]
- Defer loading of heavy components using the @defer block syntax available in modern Angular templates. [Confidence: 100%]