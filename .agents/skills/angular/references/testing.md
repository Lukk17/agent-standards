# Testing Angular

What to use, what to query by, and how to keep HTTP out of unit tests.

---

### Runners and libraries

- Unit-test components and services with TestBed, run by Jest through `jest-preset-angular`, or by Vitest.
- Use `@testing-library/angular` for component tests.
- Write browser end-to-end tests with Playwright (`@playwright/test`). Protractor is deprecated and is not an option.

---

### Query by role and label, never by selector

A test that queries `.btn-primary` breaks when the class changes and passes when the button is invisible to a screen
reader. Querying the way a user finds the control keeps the test honest about both.

```typescript
// PASS: finds the control the way a user does
const submit = screen.getByRole('button', { name: /save profile/i });
await userEvent.click(submit);
expect(await screen.findByRole('alert')).toHaveTextContent(/saved/i);
```

```typescript
// FAIL: coupled to markup, and blind to whether the control is reachable at all
const submit = fixture.nativeElement.querySelector('.btn-primary');
submit.click();
expect(component.saved).toBe(true);
```

Asserting on a private component field, as the failing example does, tests the implementation rather than the
behaviour. Assert on what the template renders.

---

### Mock HTTP at the transport, not the client

`provideHttpClientTesting` swaps the backend, so the real `HttpClient`, the real interceptors, and the real error
handling all still run. Mocking `HttpClient` itself skips all three and tests nothing worth testing.

```typescript
// PASS: real client, faked backend, request assertions available
describe('WidgetService', () => {
  let service: WidgetService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), WidgetService],
    });
    service = TestBed.inject(WidgetService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('requests the widget list once', () => {
    service.list().subscribe((widgets) => expect(widgets).toHaveLength(2));

    const req = httpMock.expectOne('/api/widgets');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: '1' }, { id: '2' }]);
  });
});
```

```typescript
// FAIL: the client is a stub, so interceptors, headers, and error mapping are never exercised
const httpClient = { get: jest.fn().mockReturnValue(of([])) };
```

`httpMock.verify()` in `afterEach` fails the test on any request the code made and the test did not expect, which is
how an accidental extra call gets caught.

---

### Testing signals and functional guards

A functional guard is a function, so it needs no TestBed harness. Run it inside an injection context and assert on
what it returns.

```typescript
it('redirects an anonymous visitor to the login page', () => {
  TestBed.configureTestingModule({
    providers: [{ provide: AuthService, useValue: { isAuthenticated: () => false } }],
  });

  const result = TestBed.runInInjectionContext(() =>
    authGuard({} as ActivatedRouteSnapshot, { url: '/dashboard' } as RouterStateSnapshot)
  );

  expect(result).toBeInstanceOf(UrlTree);
});
```

Signals are read synchronously, so a store test needs no fake async at all: call the method, read the signal, assert.

```typescript
it('adds a line and recomputes the total', () => {
  const store = TestBed.inject(CartStore);
  store.add({ id: '1', price: 12 });
  expect(store.total()).toBe(12);
});
```
