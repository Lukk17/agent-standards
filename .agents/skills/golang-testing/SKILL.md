---
name: golang-testing
description: Go testing with the standard library, covering the red-green loop, table-driven tests and subtests, hand-written fakes, golden files, synctest for concurrent code, integration tests, benchmarks, fuzzing, and coverage. Use when writing tests for a Go package, converting copy-pasted tests into a table, testing an HTTP handler, benchmarking a hot path, or testing code that waits on time. Not for production Go idioms and package design, use `golang-patterns`.
---

# Go Testing Patterns

How a Go test suite is written with nothing but `testing` and the standard library: what a test asserts, what gets
faked, and what the coverage number means. Table, fake, integration, and benchmark depth lives in the reference files
listed near the bottom.

Baseline: Go 1.25, the current stable toolchain. That gives per-iteration range variables, `t.Context`, `t.Chdir`,
and a stable `testing/synctest`, all of which the examples use.

---

### When to activate

- Writing tests for a new or changed Go function, method, or handler.
- Adding coverage to a package that has little or none.
- Diagnosing a flaky, slow, or order-dependent Go test.
- Deciding what to fake and what to run for real.
- Writing a benchmark, a fuzz target, or a golden-file test.

---

### When not to activate

- Writing the production code the tests cover. Use `golang-patterns`.
- Applying the language-neutral red-green-refactor loop and the test pyramid. Use `tdd-workflow`.
- Driving a browser through a user journey. Use `e2e-testing`.
- Exercising a whole running stack as a capability sweep. Use `e2e-runbooks`.
- Setting up the CI pipeline itself. Use `deployment-patterns`.

---

### Write the failing test first

Write the signature, write the test, watch it fail, then implement. A test written after the code passes on the first
run and has never demonstrated that it can catch anything.

Pass, in this order:

```go
func TestAdd(t *testing.T) {
    if got := Add(2, 3); got != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", got)
    }
}
```

Fail:

```go
func TestAdd(t *testing.T) {
    _ = Add(2, 3)
}
```

Read the failure before implementing. A test that fails on a compile error has not been seen to fail for the right
reason.

---

### Make the table the default shape

A table plus `t.Run` gives one named subtest per case, so the report names the input that broke rather than a line
number. Depth, including error cases and comparison helpers, is in
[references/table-tests.md](references/table-tests.md).

Pass:

```go
tests := []struct {
    name string
    a, b int
    want int
}{
    {"positive", 2, 3, 5},
    {"mixed signs", -1, 1, 0},
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        if got := Add(tt.a, tt.b); got != tt.want {
            t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.want)
        }
    })
}
```

Fail:

```go
func TestAddPositive(t *testing.T) { ... }
func TestAddNegative(t *testing.T) { ... }
func TestAddMixed(t *testing.T) { ... }
```

Range variables are per-iteration from Go 1.22, so the old `tt := tt` copy inside the loop is dead code. Delete it
wherever it still appears.

---

### Report with Errorf, stop with Fatalf

`Errorf` records the failure and keeps going, which is what you want for independent assertions. `Fatalf` stops the
test, which is what you want when continuing would panic on a nil result.

Pass:

```go
got, err := ParseConfig(input)
if err != nil {
    t.Fatalf("ParseConfig(%q): unexpected error: %v", input, err)
}
if got.Port != 8080 {
    t.Errorf("Port = %d; want 8080", got.Port)
}
```

Fail:

```go
got, err := ParseConfig(input)
if err != nil {
    t.Errorf("unexpected error: %v", err)
}
if got.Port != 8080 {
```

Write the message as `got X; want Y` with the input included. The message is the entire diagnosis a CI log gives you.

---

### Let the testing package own setup and cleanup

`t.Helper` moves the reported line to the caller, `t.Cleanup` runs teardown in reverse order even after a `Fatalf`,
`t.TempDir` and `t.Chdir` scope the filesystem to the test, and `t.Context` gives a context cancelled just before
cleanup runs.

Pass:

```go
func newStore(t *testing.T) *Store {
    t.Helper()
    dir := t.TempDir()
    store, err := Open(t.Context(), dir)
    if err != nil {
        t.Fatalf("open store: %v", err)
    }
    t.Cleanup(func() { store.Close() })
    return store
}
```

Fail:

```go
func newStore(t *testing.T) *Store {
    dir, _ := os.MkdirTemp("", "store")
    defer os.RemoveAll(dir)
    store, _ := Open(context.Background(), dir)
    return store
}
```

The failing version deletes the directory before the test uses it, hides the error, and leaks the store. `t.Chdir`
replaces the manual save-and-restore of the working directory and is safe because it refuses to run in a parallel
test.

---

### Fake with a struct, not a mock framework

A hand-written fake that satisfies the consumer's interface is a few lines, reads as ordinary Go, and breaks at
compile time when the interface changes. A generated mock adds a build step and a second thing to keep in sync.
Variants are in [references/mocks-and-fakes.md](references/mocks-and-fakes.md).

Pass:

```go
type stubUserStore struct {
    getUser func(ctx context.Context, id string) (*User, error)
}

func (s stubUserStore) GetUser(ctx context.Context, id string) (*User, error) {
    return s.getUser(ctx, id)
}
```

Fail:

```go
mockStore := new(MockUserStore)
mockStore.On("GetUser", mock.Anything, "123").Return(&User{Name: "Alice"}, nil)
```

The failing version matches by string, so a renamed method compiles and fails at runtime, or silently never matches.

---

### Never sleep to wait

`time.Sleep` in a test is either too short, making the test flaky, or too long, making the suite slow. For code that
waits on time or on other goroutines, `testing/synctest` runs the test in a bubble with a fake clock: time advances
instantly once every goroutine is blocked.

Pass:

```go
func TestCacheExpires(t *testing.T) {
    synctest.Test(t, func(t *testing.T) {
        cache := New(time.Minute)
        cache.Set("k", "v")

        time.Sleep(2 * time.Minute)
        synctest.Wait()

        if _, ok := cache.Get("k"); ok {
            t.Error("entry should have expired")
        }
    })
}
```

Fail:

```go
func TestCacheExpires(t *testing.T) {
    cache := New(50 * time.Millisecond)
    cache.Set("k", "v")
    time.Sleep(100 * time.Millisecond)
    if _, ok := cache.Get("k"); ok {
        t.Error("entry should have expired")
    }
}
```

Outside a bubble, synchronise on a channel or a `WaitGroup`. Sleeping is never the answer.

---

### Test through the exported API

An internal test file can reach an unexported function, and then a rename that changes nothing observable breaks the
suite. Test what a caller can call, and if a private function is hard to reach, that is usually a sign it wants to be
its own package.

Pass:

```go
package user_test

import "myproject/internal/user"
```

Fail:

```go
package user

func TestNormaliseEmailInternal(t *testing.T) { ... }
```

The `_test` package also proves the exported surface is usable from outside, which an internal test never checks.

---

### Run subtests in parallel only when they are independent

`t.Parallel` pauses the subtest until the parent returns, then runs them together. That is free speed for pure
functions and a source of interference for anything sharing a directory, a database, or a global.

Pass:

```go
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        if got := Normalise(tt.input); got != tt.want {
            t.Errorf("Normalise(%q) = %q; want %q", tt.input, got, tt.want)
        }
    })
}
```

Fail:

```go
t.Run(tt.name, func(t *testing.T) {
    t.Parallel()
    os.Setenv("REGION", tt.region)
    ...
})
```

Cleanup registered in a parallel parent runs after every parallel child finishes, so a shared fixture is still safe.
A shared mutable global is not.

---

### Cover around 90 percent of the real logic

The target is around 90 percent of the real logic, 100 percent on critical business logic, and 90 percent or better
on exported APIs. Excluding code from coverage is only for generated output such as protobuf stubs and generated
mocks, never for hand-written logic: if you wrote it by hand, it must be tested.

Run the suite the way CI runs it, with the race detector on:

```bash
go test -race -coverprofile=coverage.out ./...
```

Read which lines are missing rather than the headline number:

```bash
go tool cover -func=coverage.out
```

---

### Benchmark before you optimise, fuzz what parses input

A benchmark turns a performance claim into a number, and `-benchmem` turns an allocation claim into one too. A fuzz
target is worth writing for anything that parses untrusted bytes, because it finds the input nobody thought of.

```bash
go test -bench=. -benchmem ./...
```

```bash
go test -fuzz=FuzzParseJSON -fuzztime=30s ./...
```

Both are in [references/benchmarks.md](references/benchmarks.md), including `b.Loop`, sub-benchmarks by size, and
seed corpora.

---

### Reference files

| Open this | For |
| --- | --- |
| [references/table-tests.md](references/table-tests.md) | Table shapes, error cases, subtests, golden files, comparison |
| [references/mocks-and-fakes.md](references/mocks-and-fakes.md) | Fakes, stubs, spies, interfaces at the consumer, `httptest` |
| [references/integration.md](references/integration.md) | Real databases, containers, build tags, HTTP handler tests |
| [references/benchmarks.md](references/benchmarks.md) | Benchmarks, allocation counts, profiles, fuzzing, coverage |

---

### Related skills

- `golang-patterns` for the production code under test.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `e2e-testing` for browser journeys and the flaky-test policy.
- `e2e-runbooks` for capability sweeps against a live stack.
- `performance-optimization` for what to do with a benchmark once you have one.
- `coding-standards` for the shared engineering floor, including the FIRST properties.

---

### Checklist

- Every new behaviour has a test that was seen to fail before the code was written.
- Repeated tests that differ only by input are one table with named subtests.
- Failure messages state the input, what was got, and what was wanted.
- `Fatalf` is used wherever continuing would dereference a nil result.
- Helpers call `t.Helper`, and teardown goes through `t.Cleanup` rather than `defer` in a helper.
- Filesystem state uses `t.TempDir` and `t.Chdir`, and contexts come from `t.Context`.
- Dependencies are hand-written fakes satisfying an interface declared at the consumer.
- No `time.Sleep` anywhere: time-dependent code runs under `testing/synctest`.
- Tests live in the `_test` package and exercise the exported API.
- `t.Parallel` is only on subtests that share no mutable state.
- Coverage of real logic is around 90 percent, with exclusions only for generated code.
- `go test -race ./...` passes from the module root.
