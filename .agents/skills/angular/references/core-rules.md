# Angular Core Rules in Depth

The Pass and Fail examples and the reasoning behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Angular 22.

---

### Contents

- Declare components standalone
- Hold synchronous state in signals, not BehaviorSubject
- Tear down subscriptions with takeUntilDestroyed
- Inject dependencies with inject()
- Use the functional form of guards, interceptors, and forms
- Handle uncaught errors globally
- Keep change detection cheap

---

### Declare components standalone

Standalone components import what they use, so a component's dependencies are readable from the component itself.
Generate an NgModule only to integrate with legacy code that still requires one.

```typescript
// PASS: dependencies declared where they are used
@Component({
  selector: 'app-widget-list',
  imports: [WidgetCardComponent],
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
@Component({ selector: 'app-search' })
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
@Component({ selector: 'app-profile' })
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
remove on sight: a function composes and tests with no component fixture, only an injection context, and a typed
form catches a renamed control at compile time instead of at runtime.

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
[references/routing-http-and-forms.md](routing-http-and-forms.md).

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

`OnPush`, the default from Angular 22, narrows re-rendering to the inputs and signals a component actually reads. On
a project older than Angular 22, set `changeDetection: ChangeDetectionStrategy.OnPush` on each component explicitly. A function call in a template
runs on every check, which is what makes a template-bound method the most common Angular performance bug.

```html
<!-- PASS: bound to a signal, evaluated when it changes -->
<p>{{ totalPrice() }}</p>

<!-- FAIL: recomputed on every change detection cycle -->
<p>{{ calculateTotalPrice(items) }}</p>
```

Defer heavy sections with `@defer` so they load on interaction or when they enter the viewport rather than on first paint. Keep constructors free of work and put initialisation in `ngOnInit`, except for wiring that needs the injection context, such as `takeUntilDestroyed()`, `toSignal` and `effect`, which belongs in the constructor. Follow the Angular style guide for file names: hyphens between words, and a file name matching the class it exports, so a `UserProfile` component lives in `user-profile.ts` with `user-profile.html`, `user-profile.css` and `user-profile.spec.ts` beside it. Keep a `.component.ts` type suffix only in a project that already uses that convention throughout.
