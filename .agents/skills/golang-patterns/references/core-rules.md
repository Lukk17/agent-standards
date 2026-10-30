# Go Core Rules in Depth

The BAD and GOOD examples, the reasoning, and the trap table behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Go 1.27.

---

### Contents

- Make the zero value useful, and inject what it cannot hold
- Accept interfaces, return structs, and declare them at the consumer
- Doc comments on every exported name
- Wrap every error with context
- Take a context first, and never start a goroutine you cannot stop
- Test it, and watch the test fail first
- Startup readiness log
- Avoid the classic traps

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

### Doc comments on every exported name

Doc comments follow the Doc Comments rules in `coding-standards`, with one Go delta that overrides its default of none: every exported name gets a doc comment, because `go doc` and pkg.go.dev render it and the Go project asks for one on every exported identifier. Start it with the name, keep it to one sentence plus only what the signature cannot carry, and name the error conditions and the sentinels a caller can match with `errors.Is`, since the signature says only `error`. Unexported code follows the default of none.

```go
// Reserve holds stock for an order until the payment window closes.
// holdFor is capped at 15 minutes.
// Returns ErrInsufficientStock when the warehouse cannot cover the order.
func (w *Warehouse) Reserve(orderID OrderID, holdFor time.Duration) (Reservation, error)
```

---

### Wrap every error with context

`%w` keeps the original error matchable by `errors.Is` and `errors.AsType` while adding the operation that failed. Naked
returns of a library error give a caller a message with no idea which call produced it. Write the wrap message as a
lowercase operation phrase with no trailing punctuation, so the chain reads as one sentence when it is finally
printed. `_` on an error is a decision to continue with unknown state: handle it, wrap it, or, where nothing can be
done, assign it explicitly so the choice is visible in review. Sentinel errors, custom types, and matching are in
[references/errors.md](errors.md).

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
[references/concurrency.md](concurrency.md).

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
and fuzzing are in [references/testing.md](testing.md).

---

### Startup readiness log

The banner, the section order, the 2-second probe timeout, and the `<url> [Connected|Warning|FAILED]` result format
are one convention shared by every language, owned by `observability-and-logging`. What is Go-specific is where it is
emitted, after `net.Listen` returns and before `srv.Serve(listener)` blocks, so the port is already bound when the
banner says so, and that it goes through one `log/slog` call with a leading newline, because slog stamps a timestamp and
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
| `wg.Add(1)` then `go func() { defer wg.Done() ... }()` | `wg.Go(func() { ... })` |
| `var target *T` then `errors.As(err, &target)` | `target, ok := errors.AsType[*T](err)` |
| `time.Sleep` to wait in a test | `testing/synctest`, or a channel the test blocks on |
