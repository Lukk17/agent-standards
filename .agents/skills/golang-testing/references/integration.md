# Go Integration Tests

Running the real database, the real broker, and the real router, without making the fast test loop pay for it. Open
this when a unit test would only be testing a fake.

---

### Separate the slow set with a build tag

A build tag keeps integration tests out of the default `go test ./...` run and needs no naming convention anybody has
to remember.

```go
//go:build integration

package repository_test
```

Fast loop, which excludes the tagged files:

```bash
go test ./...
```

Full run:

```bash
go test -tags=integration -race ./...
```

`testing.Short()` is the lighter alternative when the test belongs in the same file as its unit tests.

```go
if testing.Short() {
    t.Skip("needs a database")
}
```

```bash
go test -short ./...
```

Pick one mechanism per repository. Two conventions for the same thing means half the suite gets skipped by accident.

---

### Start the dependency once per package with TestMain

`TestMain` runs before any test in the package and is the right place for a container that several tests share. Call
`os.Exit` with the result, and make sure the teardown runs before it.

```go
var testDB *sql.DB

func TestMain(m *testing.M) {
    ctx := context.Background()
    container, err := postgres.Run(ctx, "postgres:17-alpine")
    if err != nil {
        log.Fatalf("start postgres: %v", err)
    }

    dsn, err := container.ConnectionString(ctx, "sslmode=disable")
    if err != nil {
        log.Fatalf("connection string: %v", err)
    }
    testDB, err = sql.Open("pgx", dsn)
    if err != nil {
        log.Fatalf("open db: %v", err)
    }

    code := m.Run()

    _ = testDB.Close()
    _ = container.Terminate(ctx)
    os.Exit(code)
}
```

`os.Exit` skips deferred functions, which is why the cleanup here is written out before it rather than deferred.

Pin the image to the major version production runs. A tag of `latest` turns an upstream release into a build failure
nobody chose.

---

### Isolate each test inside a transaction

A transaction begun before the test and rolled back after gives real SQL and real constraints with no cleanup code
and no cross-test interference.

```go
func newTx(t *testing.T) *sql.Tx {
    t.Helper()
    tx, err := testDB.BeginTx(t.Context(), nil)
    if err != nil {
        t.Fatalf("begin: %v", err)
    }
    t.Cleanup(func() { _ = tx.Rollback() })
    return tx
}
```

Pass:

```go
func TestInsertUserIsRetrievable(t *testing.T) {
    repo := repository.New(newTx(t))

    if err := repo.Insert(t.Context(), &User{Name: "Alice"}); err != nil {
        t.Fatalf("insert: %v", err)
    }

    got, err := repo.GetByName(t.Context(), "Alice")
    if err != nil {
        t.Fatalf("get: %v", err)
    }
    if got.Name != "Alice" {
        t.Errorf("Name = %q; want %q", got.Name, "Alice")
    }
}
```

Fail:

```go
func TestInsertUser(t *testing.T) {
    repo := repository.New(testDB)
    _ = repo.Insert(context.Background(), &User{Name: "Alice"})
}
```

The failing version leaves a row behind, so the second run of the suite hits a unique constraint and the test that
looked fine yesterday fails today.

Code that manages its own transactions cannot be handed one. Give those tests a truncation helper in `t.Cleanup`
instead, and do not run them in parallel with each other.

---

### Test the router, not the handler, when routing is the point

`ServeHTTP` on the assembled router exercises middleware, path parameters, and the not-found path. Calling the
handler function directly skips all three.

```go
func TestAPIRoutes(t *testing.T) {
    tests := []struct {
        name       string
        method     string
        path       string
        body       string
        wantStatus int
    }{
        {"get user", http.MethodGet, "/users/123", "", http.StatusOK},
        {"missing user", http.MethodGet, "/users/999", "", http.StatusNotFound},
        {"create user", http.MethodPost, "/users", `{"name":"Bob"}`, http.StatusCreated},
        {"wrong method", http.MethodDelete, "/users", "", http.StatusMethodNotAllowed},
    }

    router := NewRouter(newTestService(t))

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            var body io.Reader
            if tt.body != "" {
                body = strings.NewReader(tt.body)
            }
            req := httptest.NewRequestWithContext(t.Context(), tt.method, tt.path, body)
            req.Header.Set("Content-Type", "application/json")
            rec := httptest.NewRecorder()

            router.ServeHTTP(rec, req)

            if rec.Code != tt.wantStatus {
                t.Errorf("status = %d; want %d", rec.Code, tt.wantStatus)
            }
        })
    }
}
```

---

### Assert on the contract, not on the whole body

Comparing the entire JSON body fails on every additive field, so the test becomes a change-detector rather than a
check. Decode into the response type and assert on what the contract promises.

Pass:

```go
var got UserResponse
if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
    t.Fatalf("decode: %v", err)
}
if got.Name != "Bob" {
    t.Errorf("Name = %q; want %q", got.Name, "Bob")
}
```

Fail:

```go
if rec.Body.String() != `{"id":"1","name":"Bob","created_at":"2026-01-01T00:00:00Z"}` {
    t.Error("body mismatch")
}
```

---

### Keep the integration suite honest in CI

Run the full set on every pull request, with the race detector, and give it a timeout so a hung container fails the
job instead of burning the runner.

```bash
go test -tags=integration -race -timeout=10m ./...
```

If the integration suite is too slow to run on every change, the fix is a faster fixture, not a nightly-only job that
nobody reads.
