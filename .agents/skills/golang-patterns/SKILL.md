---
name: golang-patterns
description: Idiomatic Go for production services, covering zero values, interface design, error wrapping, context and cancellation, dependency injection, allocation discipline, and golangci-lint v2 configuration. Use when writing a new Go package, reviewing Go code, fixing a goroutine leak, designing an interface at the consumer, or setting up Go linting. Not for writing Go tests, benchmarks, or fuzzing, use `golang-testing`.
---

# Go Development Patterns

Language-level rules for production Go: how types are shaped, how errors travel, how goroutines are stopped, and how
a module is laid out. The deeper catalogues live in the reference files listed near the bottom.

Baseline: Go 1.25, the current stable toolchain. Confirm with `go version` in the project before assuming an older
release, because the examples use per-iteration loop variables, `any`, and `log/slog` without a compatibility note.

---

### When to activate

- Writing a new Go package, command, or service.
- Reviewing or refactoring existing Go code.
- Designing an interface, a constructor, or a package boundary.
- Chasing a goroutine leak, a data race, or an ignored error.
- Setting up `golangci-lint`, `go vet`, and the formatting gate.

---

### When not to activate

- Writing tests, table tests, benchmarks, or fuzz targets. Use `golang-testing`.
- Setting up log formats, metrics, tracing, or health endpoints. Use `observability-and-logging`.
- Applying the cross-language design floor of SOLID, DRY, and naming. Use `coding-standards`.
- Designing the HTTP or gRPC contract itself. Use `api-design`.
- Profiling a slow path before changing it. Use `performance-optimization`.

---

### Keep it obvious

Go rewards the boring version. A reader should be able to follow control flow top to bottom without unwinding a
closure or a chain of helpers.

Pass:

```go
func GetUser(id string) (*User, error) {
    user, err := db.FindUser(id)
    if err != nil {
        return nil, fmt.Errorf("get user %s: %w", id, err)
    }
    return user, nil
}
```

Fail:

```go
func GetUser(id string) (*User, error) {
    if u, e := db.FindUser(id); e == nil {
        return u, nil
    } else {
        return nil, e
    }
}
```

---

### Make the zero value useful

A type whose zero value works needs no constructor, cannot be half-initialised, and composes into other structs for
free. A nil map or a nil channel inside a struct panics on first use instead.

Pass:

```go
type Counter struct {
    mu    sync.Mutex
    count int
}
```

Fail:

```go
type Counter struct {
    counts map[string]int
}
```

When a field genuinely cannot have a useful zero, give the type a constructor and keep the field unexported so it
cannot be skipped.

---

### Accept interfaces, return structs

An interface parameter lets a caller pass anything that fits. An interface return hides the concrete type from the
caller for no benefit and blocks them from reaching a method the interface does not declare.

Pass:

```go
func ProcessData(r io.Reader) (*Result, error)
```

Fail:

```go
func ProcessData(r io.Reader) (io.Reader, error)
```

---

### Define small interfaces where they are consumed

The consumer knows what it needs. An interface declared next to the implementation grows to mirror the struct, and
every consumer then depends on methods it never calls.

Pass:

```go
package service

type UserStore interface {
    GetUser(ctx context.Context, id string) (*User, error)
}
```

Fail:

```go
package postgres

type UserRepository interface {
    GetUser(ctx context.Context, id string) (*User, error)
    SaveUser(ctx context.Context, u *User) error
    ListUsers(ctx context.Context, page int) ([]*User, error)
    Migrate(ctx context.Context) error
}
```

---

### Doc comments: default to none

A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract the unclear block
into a well-named function, rename the parameters so they carry their own meaning, and tighten the types. Do that
first and most doc comments have nothing left to say, which is the outcome you want. Code that explains itself cannot
go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every note you add about a
parameter, the result, or an error is capped at one line and only appears when it genuinely adds something: if the
note does not fit on a single line, shorten it or drop it. Four rules decide what goes in. Exported identifiers are
not an automatic exception: a linter wanting a comment on every exported name is not a reason to write a sentence
that adds nothing.

1. Prose. One sentence, starting with the identifier name, saying what it does, then only what a caller cannot infer
   from the signature. Nothing more.
2. Describe a parameter only when the name and the type do not already convey it, meaning units, nullability, a valid
   range, or who owns it afterwards. `orderID is the order identifier` is noise, delete it.
3. Describe the result only when it is non-obvious.
4. Describe the error conditions always, every one a caller can act on, and name the sentinel errors it can match
   with `errors.Is`. The signature says only `error`, so this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a note line has no exception at all: shorten it or
delete it.

Pass:

```go
// Reserve holds stock for an order until the payment window closes.
// holdFor is capped at 15 minutes.
// Returns ErrInsufficientStock when the warehouse cannot cover the order.
func (w *Warehouse) Reserve(orderID OrderID, holdFor time.Duration) (Reservation, error)
```

Fail:

```go
// Reserve reserves stock. It takes an order ID and a hold duration and
// returns a reservation and an error.
func (w *Warehouse) Reserve(orderID OrderID, holdFor time.Duration) (Reservation, error)
```

---

### Wrap every error with context

`%w` keeps the original error matchable by `errors.Is` and `errors.As` while adding the operation that failed. Naked
returns of a library error give a caller a message with no idea which call produced it. Sentinel errors, custom
types, and matching are in [references/errors.md](references/errors.md).

Pass:

```go
if err := json.Unmarshal(data, &cfg); err != nil {
    return nil, fmt.Errorf("parse config %s: %w", path, err)
}
```

Fail:

```go
if err := json.Unmarshal(data, &cfg); err != nil {
    return nil, err
}
```

Write the wrap message as a lowercase operation phrase with no trailing punctuation, so the chain reads as one
sentence when it is finally printed. `_` on an error is a decision to continue with unknown state: handle it, wrap
it, or, in the rare case where nothing can be done, assign it explicitly so the choice is visible in review.

---

### Take a context first and honour cancellation

A `context.Context` is the first parameter, never a struct field. Every blocking call in the function passes it down,
so a cancelled request stops work instead of finishing it for nobody.

Pass:

```go
func FetchUser(ctx context.Context, id string) (*User, error)
```

Fail:

```go
type Request struct {
    ctx context.Context
    ID  string
}
```

---

### Never start a goroutine you cannot stop

Every goroutine needs a defined way to end: a closed channel, a cancelled context, or a `WaitGroup` the caller waits
on. A goroutine blocked forever on an unbuffered send is a leak that only shows up as memory growth in production.
Worker pools, `errgroup`, and graceful shutdown are in [references/concurrency.md](references/concurrency.md).

Pass:

```go
go func() {
    select {
    case ch <- data:
    case <-ctx.Done():
    }
}()
```

Fail:

```go
go func() {
    ch <- data
}()
```

---

### Inject dependencies instead of holding package state

A package-level `*sql.DB` initialised in `init()` cannot be swapped in a test, cannot fail loudly at startup, and
ties every consumer of the package to one instance.

Pass:

```go
type Server struct {
    db *sql.DB
}

func NewServer(db *sql.DB) *Server {
    return &Server{db: db}
}
```

Fail:

```go
var db *sql.DB

func init() {
    db, _ = sql.Open("postgres", os.Getenv("DATABASE_URL"))
}
```

---

### Allocate once when the size is known

`append` to a nil slice regrows and copies. Give `make` the capacity you already know, and build strings with
`strings.Builder` or `strings.Join` rather than `+=` in a loop.

Pass:

```go
results := make([]Result, 0, len(items))
for _, item := range items {
    results = append(results, process(item))
}
```

Fail:

```go
var results []Result
for _, item := range items {
    results = append(results, process(item))
}
```

Measure before going further. `sync.Pool` and buffer reuse are worth it in a hot path and are pure overhead
everywhere else, so reach for them after a benchmark says so, not before.

---

### Startup readiness log

The banner, the section order, the 2-second probe timeout, and the `<url> [Connected|Warning|FAILED]` result format
are one convention shared by every language, owned by `observability-and-logging`. What is Go-specific is where it is
emitted and that it goes through one `log/slog` call with a leading newline, because slog stamps a timestamp and
level per call and per-line emission would shred the banner.

```go
logger.Info("\n" + buildStartupLog())
if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
    logger.Error("server failed", "error", err)
    os.Exit(1)
}
```

Probe with `http.Client{Timeout: 2 * time.Second}` so an unreachable dependency cannot stall startup. Log the detail
at debug and surface only the result in the banner.

```go
slog.Debug("startup probe failed", "url", url, "err", err)
```

---

### Avoid the classic traps

| Trap | Do instead |
| --- | --- |
| Naked `return` in a long function | Name the returned values at the `return` statement |
| `panic` for an expected failure | Return an error and let the caller decide |
| `context.Context` stored in a struct | Pass it as the first parameter |
| Mixing value and pointer receivers on one type | Pick one and use it for every method |
| `interface{}` in a new signature | `any`, or a concrete type or type parameter |
| `time.Sleep` to wait for a goroutine | A channel, a `WaitGroup`, or a context deadline |

---

### Reference files

| Open this | For |
| --- | --- |
| [references/errors.md](references/errors.md) | Sentinels, custom error types, `errors.Is`/`As`, joining, panics |
| [references/concurrency.md](references/concurrency.md) | Worker pools, `errgroup`, channels, shutdown, `sync.Pool` |
| [references/project-layout.md](references/project-layout.md) | Module layout, package naming, options pattern, embedding |
| [references/tooling.md](references/tooling.md) | Build and test commands, `golangci-lint` v2 configuration, CI |

---

### Related skills

- `golang-testing` for table tests, fakes, benchmarks, fuzzing, and coverage.
- `coding-standards` for the cross-language floor this skill sits on.
- `observability-and-logging` for slog discipline, metrics, and the startup readiness log.
- `api-design` for the shape of the HTTP or gRPC contract a Go service serves.
- `performance-optimization` for measuring before optimising.
- `docker-patterns` for building and shipping the resulting binary.

---

### Checklist

- Every exported type has a useful zero value, or an unexported field and a constructor.
- Functions accept interfaces and return concrete types, and interfaces are declared at the consumer.
- Doc comments are absent, or one sentence plus only the notes the signature cannot carry.
- Every error a caller can act on is documented, including the sentinels it can match.
- Every returned error is wrapped with `%w` and a lowercase operation phrase.
- No error is discarded with `_` without an explicit, reviewed reason.
- `context.Context` is the first parameter everywhere and is passed to every blocking call.
- Every goroutine has a defined way to stop, and the shutdown path waits for it.
- Dependencies are injected through a constructor, with no package-level mutable state.
- Slices are preallocated where the length is known and strings are built with a `Builder`.
- `gofmt`, `go vet`, `golangci-lint run`, and `go test -race ./...` all pass.
