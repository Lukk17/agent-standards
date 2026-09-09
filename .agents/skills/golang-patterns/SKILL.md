---
name: golang-patterns
description: Idiomatic Go for production services and the test suite that proves them, covering zero values, interface design, error wrapping, context and cancellation, dependency injection, allocation discipline, golangci-lint v2, table-driven tests, hand-written fakes, benchmarks, and fuzzing. Use when writing a new Go package, reviewing Go code, fixing a goroutine leak, designing an interface at the consumer, setting up Go linting, converting copy-pasted tests into a table, testing an HTTP handler, or benchmarking a hot path. Not for the language-neutral SOLID, DRY, and naming floor, use `coding-standards`.
---

# Go Development Patterns

Language-level rules for production Go and the test suite that proves it: how types are shaped, how errors travel,
how goroutines are stopped, how a module is laid out, and how it is tested. Go rewards the boring version, so a
reader should follow control flow top to bottom without unwinding a closure. The hub carries the rules that decide
most reviews, each reference file the depth for one area.

Baseline: Go 1.25, the current stable toolchain. Confirm with `go version` before assuming an older release: the
examples use per-iteration loop variables, `any`, `log/slog`, and `testing/synctest` with no compatibility note.

---

### When to activate

- Writing, reviewing, or refactoring a Go package, command, or service.
- Designing an interface, a constructor, or a package boundary, or chasing a goroutine leak or a data race.
- Setting up `golangci-lint`, `go vet`, and the formatting gate.
- Writing table tests, fakes, benchmarks, or fuzz targets, or raising coverage on a package.

---

### When not to activate

- Applying the cross-language design floor of SOLID, DRY, and naming. Use `coding-standards`.
- Applying the language-neutral red-green-refactor loop and the test pyramid. Use `tdd-workflow`.
- Setting up log formats, metrics, tracing, or health endpoints. Use `observability-and-logging`.
- Designing the HTTP or gRPC contract the service serves. Use `api-design`.
- Profiling a slow path before changing it. Use `performance-optimization`.
- Driving a browser through a user journey. Use `e2e-testing`.

---

### Make the zero value useful, and inject what it cannot hold

A type whose zero value works needs no constructor, cannot be half-initialised, and composes into other structs for
free, while a nil map or a nil channel inside a struct panics on first use. When a field genuinely cannot have a
useful zero, give the type a constructor, keep the field unexported so it cannot be skipped, and take the dependency
as an argument. A package-level `*sql.DB` initialised in `init()` cannot be swapped in a test, cannot fail loudly at
startup, and ties every consumer of the package to one instance.

```go
// BAD
type Counter struct {
    counts map[string]int
}

var db *sql.DB

func init() {
    db, _ = sql.Open("postgres", os.Getenv("DATABASE_URL"))
}

// GOOD
type Counter struct {
    mu    sync.Mutex
    count int
}

func NewServer(db *sql.DB) *Server {
    return &Server{db: db}
}
```

---

### Accept interfaces, return structs, and declare them at the consumer

An interface parameter lets a caller pass anything that fits, while an interface return hides the concrete type for
no benefit and blocks the caller from reaching a method the interface does not declare. The consumer also knows what
it needs: an interface declared next to the implementation grows to mirror the struct, and every consumer then
depends on methods it never calls.

```go
// BAD. Declared in package postgres, mirroring the repository struct.
type UserRepository interface {
    GetUser(ctx context.Context, id string) (*User, error)
    SaveUser(ctx context.Context, u *User) error
    Migrate(ctx context.Context) error
}

// GOOD. Declared in package service, holding only what the service calls.
type UserStore interface {
    GetUser(ctx context.Context, id string) (*User, error)
}

func ProcessData(r io.Reader) (*Result, error)
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

```go
// GOOD. One sentence, then only what the signature cannot carry, one line per note.
// Reserve holds stock for an order until the payment window closes.
// holdFor is capped at 15 minutes.
// Returns ErrInsufficientStock when the warehouse cannot cover the order.
func (w *Warehouse) Reserve(orderID OrderID, holdFor time.Duration) (Reservation, error)
```

The failing shape on the same function is `Reserve reserves stock. It takes an order ID and a hold duration and
returns a reservation and an error.`, which restates the signature and says nothing about the failure mode.

---

### Wrap every error with context

`%w` keeps the original error matchable by `errors.Is` and `errors.As` while adding the operation that failed. Naked
returns of a library error give a caller a message with no idea which call produced it. Write the wrap message as a
lowercase operation phrase with no trailing punctuation, so the chain reads as one sentence when it is finally
printed. `_` on an error is a decision to continue with unknown state: handle it, wrap it, or, where nothing can be
done, assign it explicitly so the choice is visible in review. Sentinel errors, custom types, and matching are in
[references/errors.md](references/errors.md).

```go
// BAD
if err := json.Unmarshal(data, &cfg); err != nil {
    return nil, err
}

// GOOD
if err := json.Unmarshal(data, &cfg); err != nil {
    return nil, fmt.Errorf("parse config %s: %w", path, err)
}
```

---

### Take a context first, and never start a goroutine you cannot stop

A `context.Context` is the first parameter, never a struct field, and every blocking call in the function passes it
down so a cancelled request stops work instead of finishing it for nobody. That context is also the usual way a
goroutine ends: every one needs a defined way out, whether a closed channel, a cancelled context, or a `WaitGroup`
the caller waits on. A goroutine blocked forever on an unbuffered send is a leak that only shows up as memory growth
in production. Worker pools, `errgroup`, and graceful shutdown are in
[references/concurrency.md](references/concurrency.md).

```go
// BAD. Context parked on a struct, and a send nothing can cancel.
type Request struct {
    ctx context.Context
}

go func() { ch <- data }()

// GOOD
func FetchUser(ctx context.Context, id string) (*User, error)

go func() {
    select {
    case ch <- data:
    case <-ctx.Done():
    }
}()
```

---

### Test it, and watch the test fail first

Write the signature, write the test, watch it fail, then implement. A test written after the code passes on the first
run has never demonstrated it can catch anything. A table plus `t.Run` is the default shape, because the report then
names the input that broke rather than a line number, and the message reads `got X; want Y` with the input in it.

```go
// BAD
func TestAddPositive(t *testing.T) { ... }
func TestAddNegative(t *testing.T) { ... }

// GOOD
for _, tt := range []struct {
    name    string
    a, b    int
    want    int
}{{"positive", 2, 3, 5}, {"mixed signs", -1, 1, 0}} {
    t.Run(tt.name, func(t *testing.T) {
        if got := Add(tt.a, tt.b); got != tt.want {
            t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.want)
        }
    })
}
```

Fake a dependency with a hand-written struct satisfying the interface the consumer declared, never with a mock
framework that matches method names by string. Fake only what you cannot run: a payment API is fair, the database is
not when a container or an in-memory engine exercises the real query.

Cover around 90 percent of the real logic, 100 percent on critical business logic, and exclude only generated output
such as protobuf stubs. A failing coverage gate is a signal to add the missing test, never to lower the threshold.
Run the suite the way CI runs it, from the module root, with the race detector on:

```bash
go test -race -coverprofile=coverage.out ./...
```

Test shape, `t.Cleanup` and `t.Context`, `testing/synctest` instead of `time.Sleep`, parallel subtests, benchmarks,
and fuzzing are in [references/testing.md](references/testing.md).

---

### Startup readiness log

The banner, the section order, the 2-second probe timeout, and the `<url> [Connected|Warning|FAILED]` result format
are one convention shared by every language, owned by `observability-and-logging`. What is Go-specific is where it is
emitted and that it goes through one `log/slog` call with a leading newline, because slog stamps a timestamp and
level per call and per-line emission would shred the banner, so the whole block is one `logger.Info` of the built
string. Probe with `http.Client{Timeout: 2 * time.Second}` so an unreachable dependency cannot stall startup, log the
detail at debug with `slog.Debug`, and surface only the result in the banner.

```go
logger.Info("\n" + buildStartupLog())
```

---

### Avoid the classic traps

| Trap | Do instead |
| --- | --- |
| Naked `return` in a long function | Name the returned values at the `return` statement |
| `if err == nil { ... } else { ... }` | Return early on the error and leave the happy path unindented |
| `var results []T` then `append` in a loop | `make([]T, 0, len(items))`, and `strings.Builder` for strings |
| `panic` for an expected failure | Return an error and let the caller decide |
| `context.Context` stored in a struct | Pass it as the first parameter |
| Mixing value and pointer receivers on one type | Pick one and use it for every method |
| `interface{}` in a new signature | `any`, or a concrete type or type parameter |
| `time.Sleep` to wait for a goroutine | A channel, a `WaitGroup`, or a context deadline |
| `time.Sleep` to wait in a test | `testing/synctest`, or a channel the test blocks on |

---

### Reference files

| Open this | For |
| --- | --- |
| [references/errors.md](references/errors.md) | Sentinels, custom error types, `errors.Is`/`As`, joining, panics |
| [references/concurrency.md](references/concurrency.md) | Worker pools, `errgroup`, channels, shutdown, `sync.Pool` |
| [references/project-layout.md](references/project-layout.md) | Module layout, package naming, options pattern, embedding |
| [references/tooling.md](references/tooling.md) | Build and test commands, `golangci-lint` v2 configuration, CI |
| [references/testing.md](references/testing.md) | Test shape, `t.Cleanup`, `synctest`, parallel subtests, coverage |
| [references/table-tests.md](references/table-tests.md) | Table shapes, error cases, subtests, golden files, comparison |
| [references/mocks-and-fakes.md](references/mocks-and-fakes.md) | Fakes, stubs, spies, interfaces at the consumer, `httptest` |
| [references/integration.md](references/integration.md) | Real databases, containers, build tags, HTTP handler tests |
| [references/benchmarks.md](references/benchmarks.md) | Benchmarks, allocation counts, profiles, fuzzing, coverage |

---

### Related skills

- `coding-standards` for the cross-language floor this skill sits on.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `observability-and-logging` for slog discipline, metrics, and the startup readiness log.
- `api-design` for the shape of the HTTP or gRPC contract a Go service serves.
- `performance-optimization` for what to do with a benchmark once you have one.
- `docker-patterns` for building and shipping the resulting binary.

---

### Checklist

- Every exported type has a useful zero value, or an unexported field and a constructor.
- Functions accept interfaces and return concrete types, and interfaces are declared at the consumer.
- Doc comments are absent, or one sentence plus only the notes the signature cannot carry.
- Every error a caller can act on is documented, including the sentinels it can match.
- Every returned error is wrapped with `%w` and a lowercase operation phrase, and none is discarded with `_`.
- `context.Context` is the first parameter everywhere and is passed to every blocking call.
- Every goroutine has a defined way to stop, and dependencies arrive through a constructor.
- Slices are preallocated where the length is known and strings are built with a `Builder`.
- Every new behaviour has a test seen to fail, repeated cases are one table, and fakes are hand-written.
- `gofmt`, `go vet`, `golangci-lint run`, and `go test -race ./...` all pass, with around 90 percent coverage.
