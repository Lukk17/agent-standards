---
name: angular
description: Angular application standards covering standalone components, signals and RxJS interop, dependency injection with inject(), OnPush change detection, functional guards and interceptors, typed reactive forms, and global error handling. Use when you say "build this Angular component", "replace this BehaviorSubject with a signal", "my subscription leaks", "write a functional auth guard", or "add an HTTP error interceptor". Not for React and Next.js work, use `react-patterns`.
license: Apache-2.0
---

# Angular Standards

Architecture and code standards for Angular applications: how components are declared, how state flows, how
dependencies arrive, and how errors are handled. Every rule here has a modern form and a legacy form, and the legacy
form is the one to remove on sight.

Baseline: current stable Angular. Standalone components, signals, RxJS interop, `inject()`, functional guards and
interceptors, and typed reactive forms are all stable, so nothing below is gated behind a flag.

---

### When to activate

- Building or reviewing any Angular component, service, guard, interceptor, or form.
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
| Functional guards and resolvers, HTTP interceptors, typed forms | [references/routing-http-and-forms.md](references/routing-http-and-forms.md) |
| Unit tests, component tests, HTTP mocking, end-to-end setup | [references/testing.md](references/testing.md) |
| Sanitisation, CSP, and internationalisation | [references/security-and-i18n.md](references/security-and-i18n.md) |

---

### Declare components standalone

Standalone components import what they use, so a component's dependencies are readable from the component itself.
Generate an NgModule only to integrate with legacy code that still requires one.

```typescript
// PASS: dependencies declared where they are used
@Component({
  selector: 'app-widget-list',
  imports: [WidgetCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@for (widget of widgets(); track widget.id) { <app-widget-card [widget]="widget" /> }`,
})
export class WidgetListComponent {}

// FAIL: a module whose only job is to declare one component
@NgModule({ declarations: [WidgetListComponent], imports: [CommonModule] })
export class WidgetListModule {}
```

---

### Hold synchronous state in signals, not BehaviorSubject

A signal is synchronously readable, needs no subscription, and cannot leak. Use it for state the UI renders. Keep
RxJS for what it is good at: asynchronous streams, event timing, and cancellation.

```typescript
// PASS: signal state, derived values computed, no subscription to manage
@Injectable({ providedIn: 'root' })
export class CartStore {
  private readonly items = signal<CartItem[]>([]);

  readonly lines = this.items.asReadonly();
  readonly total = computed(() => this.items().reduce((sum, item) => sum + item.price, 0));

  add(item: CartItem): void {
    this.items.update((current) => [...current, item]);
  }
}
```

```typescript
// FAIL: a subject, a manual derived stream, and a value nobody can read synchronously
@Injectable({ providedIn: 'root' })
export class CartStore {
  private readonly items$ = new BehaviorSubject<CartItem[]>([]);
  readonly total$ = this.items$.pipe(map((items) => items.reduce((sum, i) => sum + i.price, 0)));
}
```

To render an observable in a template, convert it with `toSignal` from `@angular/core/rxjs-interop`, or use the
`async` pipe. Never call `subscribe` in a component to assign a field.

```typescript
readonly user = toSignal(this.userService.currentUser$, { initialValue: null });
```

---

### Tear down subscriptions with takeUntilDestroyed

A subscription that outlives its component keeps the component, its template, and everything they reference alive.
`takeUntilDestroyed` reads the injection context and completes the stream automatically.

```typescript
// PASS: teardown is declared in the pipe, nothing to remember in a lifecycle hook
@Component({ selector: 'app-search', changeDetection: ChangeDetectionStrategy.OnPush })
export class SearchComponent {
  private readonly search = inject(SearchService);

  constructor() {
    this.search.query$
      .pipe(debounceTime(300), switchMap((q) => this.search.run(q)), takeUntilDestroyed())
      .subscribe((results) => this.results.set(results));
  }
}
```

```typescript
// FAIL: the legacy destroy subject, easy to forget and easy to get wrong
export class SearchComponent implements OnDestroy {
  private readonly destroy$ = new Subject<void>();

  ngOnInit(): void {
    this.search.query$.pipe(takeUntil(this.destroy$)).subscribe();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

Outside an injection context, pass a `DestroyRef` explicitly: `takeUntilDestroyed(this.destroyRef)`.

Use higher-order mapping operators deliberately: `switchMap` for a request that supersedes the last one, `concatMap`
when order must hold, `exhaustMap` to ignore a second submit while the first is in flight, `mergeMap` only when
concurrency is genuinely wanted.

---

### Inject dependencies with inject()

`inject()` removes the constructor parameter list, so a subclass never has to repeat its parent's dependencies, and
it works in field initialisers where a constructor parameter does not.

```typescript
// PASS: fields declare what they need, readonly, no constructor plumbing
@Component({ selector: 'app-profile', changeDetection: ChangeDetectionStrategy.OnPush })
export class ProfileComponent {
  private readonly userService = inject(UserService);
  private readonly router = inject(Router);
}

// FAIL: a constructor that every subclass must now restate
export class ProfileComponent {
  constructor(private userService: UserService, private router: Router) {}
}
```

Register singletons with `providedIn: 'root'` so they tree-shake when unused, and never inject `HttpClient` into a
component. API calls belong in a dedicated data service.

---

### Use the functional form of guards, interceptors, and forms

Angular still ships a class-based API alongside the modern functional one for route guards, resolvers, and HTTP
interceptors, and an untyped variant alongside typed reactive forms. In all four cases the legacy form is the one to
remove on sight: a function composes and tests without TestBed, and a typed form catches a renamed control at compile
time instead of at runtime.

```typescript
// PASS: a guard that is just a function, and a form whose shape is checked
export const authGuard: CanActivateFn = (route, state) =>
  inject(AuthService).isAuthenticated() || inject(Router).createUrlTree(['/login']);

readonly form = new FormGroup<{ email: FormControl<string> }>({
  email: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
});
```

```typescript
// FAIL: the deprecated class guard, and a form whose every read is any
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  canActivate(): boolean { return this.auth.isAuthenticated(); }
}

readonly form = new UntypedFormGroup({ email: new UntypedFormControl('') });
```

Register interceptors through `provideHttpClient(withInterceptors([...]))` in the order they should run. Full
examples, including reusable validators and resolvers, are in
[references/routing-http-and-forms.md](references/routing-http-and-forms.md).

---

### Handle uncaught errors globally

An uncaught error with no handler leaves a blank screen and nothing in the logs. A custom `ErrorHandler` captures it,
records the context that makes it diagnosable, and shows a fallback.

```typescript
// PASS: logged with the context that makes it diagnosable, user shown a fallback
@Injectable()
export class AppErrorHandler implements ErrorHandler {
  private readonly logger = inject(LoggingService);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationService);

  handleError(error: unknown): void {
    this.logger.error('Uncaught error', {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      url: this.router.url,
    });
    this.notifications.showFallback();
  }
}
```

```typescript
// FAIL: the error disappears and the stream quietly continues
this.userService.load().pipe(catchError(() => of(null))).subscribe();
```

Register it in the application config with `{ provide: ErrorHandler, useClass: AppErrorHandler }`. Never swallow an
error in `catchError` without logging it: re-throw, or convert it into a typed error the caller can render.

---

### Keep change detection cheap

`OnPush` narrows re-rendering to the inputs and signals a component actually reads. A function call in a template
runs on every check, which is what makes a template-bound method the most common Angular performance bug.

```html
<!-- PASS: bound to a signal, evaluated when it changes -->
<p>{{ totalPrice() }}</p>

<!-- FAIL: recomputed on every change detection cycle -->
<p>{{ calculateTotalPrice(items) }}</p>
```

Defer heavy sections with `@defer` so they load on interaction or when they enter the viewport rather than on first
paint. Keep constructors free of work and put initialisation in `ngOnInit`. Follow the Angular style guide for file
names: dashes between words, `feature.type.ts`, and a file name matching the class it exports.

---

### Doc Comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method or small service, rename the parameters so they carry their own meaning,
and tighten the types. Do that first and most doc comments have nothing left to say, which is the outcome you want.
Code that explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@returns` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param userId - The user identifier` is noise, delete it, and never restate a
   type TypeScript already declares.
3. `@returns` only when it is non-obvious. For an `Observable`, whether it completes, replays, or has to be
   unsubscribed is exactly the kind of thing that counts as non-obvious.
4. `@throws` always, for every error a caller can act on. TypeScript keeps throws out of the signature, so this one is
   genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```typescript
// PASS: one sentence, then only what the signature cannot say
/**
 * Loads the current user's dashboard widgets.
 *
 * @returns a cold Observable that completes after one emission
 * @throws {HttpErrorResponse} when the widget endpoint rejects the session
 */
loadWidgets(): Observable<Widget[]> { ... }

// FAIL: restates the signature
/**
 * Loads widgets.
 *
 * @param userId - The user identifier
 * @returns An observable of widgets
 */
loadWidgets(userId: string): Observable<Widget[]> { ... }
```

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

- Every new component is standalone and sets `ChangeDetectionStrategy.OnPush`.
- Synchronous UI state lives in signals, and no `BehaviorSubject` is used as a state container.
- Every component-level subscription ends with `takeUntilDestroyed`, and no `ngOnDestroy` destroy subject remains.
- No `subscribe` call in a component assigns a field that a signal or the `async` pipe could hold.
- Dependencies arrive through `inject()`, and no component injects `HttpClient` directly.
- Guards, resolvers, and interceptors are functions, not classes.
- Every reactive form is typed, and no untyped form variant remains.
- A custom `ErrorHandler` is registered, and no `catchError` discards an error without logging it.
- No template binds to a method call.
- No doc comment restates a signature, and every recoverable error is documented with `@throws`.
