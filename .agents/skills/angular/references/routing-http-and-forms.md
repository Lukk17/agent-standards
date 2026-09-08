# Guards, Interceptors, and Typed Forms

The three places Angular still ships a legacy class-based API alongside the modern functional one. Use the functional
form in all three.

---

### Write guards and resolvers as functions

A functional guard is a plain function that returns a decision. It composes, it tests without TestBed, and it uses
`inject()` for whatever it needs.

```typescript
// PASS: a function, injectable, easy to unit test
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  return auth.isAuthenticated() ? true : router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url },
  });
};
```

```typescript
// FAIL: a class implementing the deprecated interface
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  canActivate(): boolean { return this.auth.isAuthenticated(); }
}
```

Returning a `UrlTree` rather than `false` redirects instead of silently cancelling the navigation, which is almost
always what the user needs.

Use `CanDeactivate` for forms with unsaved changes. Use a `ResolveFn` only for data the component genuinely cannot
render without, and fetch anything optional inside the component so the navigation is not blocked on it.

```typescript
export const widgetResolver: ResolveFn<Widget> = (route) =>
  inject(WidgetService).get(route.paramMap.get('id')!);
```

---

### Write interceptors as functions

`HttpInterceptorFn` is a function registered through `provideHttpClient(withInterceptors([...]))`. It reads its
dependencies with `inject()` and composes with the rest of the chain in a readable order.

```typescript
// PASS: functional interceptor, dependencies injected, errors normalised on the way out
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(TokenStore).accessToken();
  const authorised = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
  return next(authorised);
};

export const errorInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(catchError((error: HttpErrorResponse) => throwError(() => toAppError(error))));
```

```typescript
// FAIL: the class-based interceptor and its HTTP_INTERCEPTORS multi-provider
@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(req.clone({ setHeaders: { Authorization: `Bearer ${this.token}` } }));
  }
}
```

Register them in the order they should run, because the chain executes in the order given.

```typescript
provideHttpClient(withInterceptors([authInterceptor, errorInterceptor]))
```

A request interceptor that attaches credentials belongs first, and the error-normalisation interceptor belongs last
so it sees failures from everything before it.

---

### Type every reactive form

An untyped form silently returns `any`, so a renamed control fails at runtime instead of at compile time. Declare the
control types and let `form.value` carry them.

```typescript
// PASS: the shape is checked, and a typo in a control name will not compile
interface ProfileForm {
  email: FormControl<string>;
  age: FormControl<number | null>;
}

readonly form = new FormGroup<ProfileForm>({
  email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
  age: new FormControl<number | null>(null),
});
```

```typescript
// FAIL: untyped, so every read is any and every control name is a guess
readonly form = new UntypedFormGroup({
  email: new UntypedFormControl(''),
  age: new UntypedFormControl(null),
});
```

`nonNullable: true` is what makes a control's type `string` rather than `string | null`, and it also makes a reset
return to the initial value instead of to null.

Use reactive forms for anything non-trivial. Template-driven forms do not scale past a couple of fields with simple
validation. Extract reusable validators into pure functions rather than inlining the logic in a component.

```typescript
export function matchesField(other: string): ValidatorFn {
  return (control) => (control.value === control.parent?.get(other)?.value ? null : { mismatch: true });
}
```

Form controls still need labels, `aria-invalid`, and error text linked with `aria-describedby`. See
`web-accessibility`.
