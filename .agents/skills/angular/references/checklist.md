# Angular Checklist

Run it before calling an Angular change or an Angular review done.

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
