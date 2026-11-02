---
name: golang-patterns
description: "Idiomatic Go 1.27 for production services and their tests, covering zero values, interfaces at the consumer, error wrapping, context and goroutine lifetimes, golangci-lint v2, table tests, hand-written fakes, benchmarks and fuzzing. Use when the user says \"review this Go package\" or \"fix this goroutine leak\". Not for the language-neutral SOLID, DRY and naming floor, use `coding-standards`."
---

# Go Development Patterns

Language-level rules for production Go and the test suite that proves it: how types are shaped, how errors travel, how goroutines are stopped, how a module is laid out, and how it is tested. Go rewards the boring version, so a reader should follow control flow top to bottom without unwinding a closure. The hub carries the rules that decide most reviews, each reference file the depth for one area.

Written for Go 1.27. Confirm with `go version` before assuming an older release: the examples use per-iteration loop variables, `any`, `log/slog`, `testing/synctest`, `sync.WaitGroup.Go`, and `errors.AsType` with no compatibility note.

---

### When to activate

- Writing, reviewing, or refactoring a Go package, command, or service.
- The user says "review this Go package", "fix this goroutine leak", "design this interface", "set up Go linting", "turn these tests into a table", "test this HTTP handler", or "benchmark this hot path".
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

### Rules

1. Make the zero value useful. A field with no useful zero stays unexported behind a constructor, and a dependency arrives as a constructor argument, never a package variable set in `init()`.
2. Accept interfaces, return structs, and declare each interface at the consumer with only the methods it calls.
3. Wrap every returned error with `%w` and a lowercase operation phrase with no trailing punctuation. Drop one only by an explicit `_ =` where nothing can be done.
4. `context.Context` is the first parameter, never a struct field, and goes to every blocking call.
5. Start no goroutine without a defined way out: a closed channel, a cancelled context, or a `WaitGroup` the caller waits on.
6. Watch every test fail first. Repeated cases are one table under `t.Run` with `got X; want Y` messages, and fakes are hand-written structs for what you cannot run, never a mock framework.
7. Cover around 90 percent of real logic and 100 percent of critical logic, exclude only generated output, and never lower the gate. Run `go test -race -coverprofile=coverage.out ./...` from the module root.
8. The startup readiness block belongs to `observability-and-logging`. Emit it after `net.Listen` and before `srv.Serve`, in one `log/slog` call with a leading newline, probing with a 2-second client timeout.
9. Avoid the legal-but-wrong traps in the core rules reference, such as `else` after an error check, `panic` for an expected failure, or `time.Sleep` to wait.

---

### Doc comments on every exported name

Doc comments follow the Doc Comments rules in `coding-standards`, with one Go delta that overrides its default of none: every exported name gets a doc comment, because `go doc` and pkg.go.dev render it and the Go project asks for one on every exported identifier. Start it with the name, keep it to one sentence plus only what the signature cannot carry, and name the error conditions and the sentinels a caller can match with `errors.Is`, since the signature says only `error`. Unexported code follows the default of none.

---

### Reference files

| Open this | When |
| --- | --- |
| [references/core-rules.md](references/core-rules.md) | A hub rule needs its BAD and GOOD example, its full reasoning, or the trap table |
| [references/errors.md](references/errors.md) | Sentinels, custom error types, `errors.Is` and `errors.AsType`, joining, panics |
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
- Every exported name has a doc comment that starts with its name, and unexported code follows the default of none.
- Every error a caller can act on is documented, including the sentinels it can match.
- Every returned error is wrapped with `%w` and a lowercase operation phrase, and none is silently dropped. An explicit `_ =` assignment appears only where nothing can be done.
- `context.Context` is the first parameter everywhere and is passed to every blocking call.
- Every goroutine has a defined way to stop, and dependencies arrive through a constructor.
- Slices are preallocated where the length is known and strings are built with a `Builder`.
- Every new behaviour has a test seen to fail, repeated cases are one table, and fakes are hand-written.
- `gofmt`, `go vet`, `golangci-lint run`, and `go test -race ./...` all pass, with around 90 percent coverage.
