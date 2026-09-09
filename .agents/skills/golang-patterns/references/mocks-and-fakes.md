# Fakes, Stubs, and Test Doubles

How to substitute a dependency in Go without a mocking framework, and how to check that the substitute is still
telling the truth. Open this when a test needs a dependency it cannot run.

---

### Declare the interface at the consumer

The interface exists so the test can substitute. It belongs in the package that calls it, listing only the methods
that package uses, which is what keeps the fake small.

```go
package service

type UserStore interface {
    GetUser(ctx context.Context, id string) (*User, error)
}

type Service struct {
    store UserStore
}

func New(store UserStore) *Service {
    return &Service{store: store}
}
```

The production implementation in another package satisfies this implicitly and never imports it, so the two can
change independently.

---

### Stub with function fields

A struct of function fields lets each test define only the behaviour it cares about, without a builder or a
registration call.

```go
type stubUserStore struct {
    getUser func(ctx context.Context, id string) (*User, error)
}

func (s stubUserStore) GetUser(ctx context.Context, id string) (*User, error) {
    return s.getUser(ctx, id)
}

func TestGetProfileReturnsName(t *testing.T) {
    svc := New(stubUserStore{
        getUser: func(_ context.Context, id string) (*User, error) {
            if id != "123" {
                return nil, ErrNotFound
            }
            return &User{ID: "123", Name: "Alice"}, nil
        },
    })

    got, err := svc.GetProfile(t.Context(), "123")
    if err != nil {
        t.Fatalf("GetProfile: %v", err)
    }
    if got.Name != "Alice" {
        t.Errorf("Name = %q; want %q", got.Name, "Alice")
    }
}
```

A nil function field panics with a clear stack when a test triggers a call it did not expect, which is exactly the
feedback you want.

---

### Fake with a real, simple implementation

When several tests need the dependency to behave, write a working in-memory version once. It is more useful than a
stub because it enforces the same invariants, and it makes multi-step tests readable.

```go
type fakeUserStore struct {
    mu    sync.Mutex
    users map[string]*User
}

func newFakeUserStore() *fakeUserStore {
    return &fakeUserStore{users: map[string]*User{}}
}

func (f *fakeUserStore) GetUser(_ context.Context, id string) (*User, error) {
    f.mu.Lock()
    defer f.mu.Unlock()
    user, ok := f.users[id]
    if !ok {
        return nil, ErrNotFound
    }
    return user, nil
}
```

Take the lock even when today's tests are sequential. The first `t.Parallel` added later will otherwise trip the race
detector in a test nobody touched.

---

### Spy when the call itself is the behaviour

Some contracts are about what was called, not what came back. Record the calls and assert on them.

```go
type spyMailer struct {
    sent []Email
}

func (s *spyMailer) Send(_ context.Context, email Email) error {
    s.sent = append(s.sent, email)
    return nil
}

func TestSignupSendsWelcomeEmail(t *testing.T) {
    mailer := &spyMailer{}

    if err := Signup(t.Context(), mailer, "alice@example.com"); err != nil {
        t.Fatalf("Signup: %v", err)
    }

    if len(mailer.sent) != 1 {
        t.Fatalf("sent %d emails; want 1", len(mailer.sent))
    }
    if mailer.sent[0].To != "alice@example.com" {
        t.Errorf("To = %q; want %q", mailer.sent[0].To, "alice@example.com")
    }
}
```

Assert on the fields the contract promises. Asserting on the full struct makes an added field break every test.

---

### Assert the fake still matches the interface

A compile-time assertion catches drift the moment the interface gains a method, without waiting for a test to fail.

```go
var _ UserStore = (*fakeUserStore)(nil)
```

---

### Fake an HTTP dependency with httptest.Server

For a client wrapping someone else's API, a real server on a real port exercises the transport, the headers, the
status handling, and the JSON decoding that a stubbed client skips entirely.

Pass:

```go
func TestClientFetchesUser(t *testing.T) {
    srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.URL.Path != "/users/123" {
            t.Errorf("path = %q; want %q", r.URL.Path, "/users/123")
        }
        w.Header().Set("Content-Type", "application/json")
        fmt.Fprint(w, `{"id":"123","name":"Alice"}`)
    }))
    t.Cleanup(srv.Close)

    got, err := NewClient(srv.URL).GetUser(t.Context(), "123")
    if err != nil {
        t.Fatalf("GetUser: %v", err)
    }
    if got.Name != "Alice" {
        t.Errorf("Name = %q; want %q", got.Name, "Alice")
    }
}
```

Fail:

```go
client := &Client{doer: stubDoer{resp: &http.Response{Body: io.NopCloser(strings.NewReader(`{}`))}}}
```

Use `httptest.NewTLSServer` and its `srv.Client()` when the code under test cares about TLS. Simulate a failure by
having the handler write a 500 or hang until the context is cancelled, which is how you test the retry path.

---

### Test a handler with httptest.NewRecorder

Handlers need no server at all. `httptest.NewRequest` builds the request and `NewRecorder` captures the response.

```go
func TestHealthHandler(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/health", nil)
    rec := httptest.NewRecorder()

    HealthHandler(rec, req)

    if rec.Code != http.StatusOK {
        t.Errorf("status = %d; want %d", rec.Code, http.StatusOK)
    }
    if rec.Body.String() != "OK" {
        t.Errorf("body = %q; want %q", rec.Body.String(), "OK")
    }
}
```

Call `ServeHTTP` on the router rather than the handler function when routing, middleware, or path parameters are part
of what you are testing.

---

### Do not fake what you can run

An in-memory store is a fake of your own code and is fine. A fake of SQL is a fake of a language with its own
semantics, and a suite that passes against it proves nothing about the database. Run the real engine instead, as
described in [integration.md](integration.md).
