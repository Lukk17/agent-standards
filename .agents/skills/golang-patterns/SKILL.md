---
name: golang-patterns
description: 'Go 1.27 patterns and tests: interfaces, errors, context, goroutines and table tests. Use when the user says "review this Go package" or "fix this goroutine leak". Not for SOLID and naming, use `coding-standards`.'
metadata:
  version: "1.1.0"
---

# Go Development Patterns

Language-level rules for production Go and the test suite that proves it: how types are shaped, how errors travel, how goroutines are stopped, how a module is laid out, and how it is tested. Go rewards the boring version, so a reader should follow control flow top to bottom without unwinding a closure.

Written for Go 1.27. Confirm with `go version` before assuming an older release: the examples use per-iteration loop variables, `any`, `log/slog`, `testing/synctest`, `sync.WaitGroup.Go`, and `errors.AsType` with no compatibility note.

---

### When not to activate

- Applying the cross-language design floor of SOLID, DRY, and naming, use `coding-standards`.
- Applying the language-neutral red-green-refactor loop and the test pyramid, use `tdd-workflow`.
- Designing the HTTP or gRPC contract the service serves, use `api-design`.

---

### Rules

1. Make the zero value useful. A field with no useful zero stays unexported behind a constructor, and a dependency arrives as a constructor argument, never a package variable set in `init()`.
2. Accept interfaces, return structs, and declare each interface at the consumer with only the methods it calls.
3. Wrap every returned error with `%w` and a lowercase operation phrase with no trailing punctuation. Drop one only by an explicit `_ =` where nothing can be done.
4. `context.Context` is the first parameter, never a struct field, and goes to every blocking call.
5. Start no goroutine without a defined way out: a closed channel, a cancelled context, or a `WaitGroup` the caller waits on.
6. Watch every test fail first. Repeated cases are one table under `t.Run` with `got X; want Y` messages, and fakes are hand-written structs for what you cannot run, never a mock framework.
7. Cover around 90 percent of real logic and 100 percent of critical logic, exclude only generated output, and never lower the gate. Run the tests with the race detector and a coverage profile from the module root.
8. A service emits its startup readiness block after `net.Listen` and before `srv.Serve`, in one `log/slog` call.
9. Avoid the legal-but-wrong traps in the core rules reference, such as `else` after an error check, `panic` for an expected failure, or `time.Sleep` to wait.
10. Doc comments follow the Doc Comments rules in `coding-standards`, with one Go delta: every exported name gets one, starting with the name and naming the errors and sentinels a caller can match.

---

### Reference files

| Open this | When |
| --- | --- |
| [core-rules.md](references/core-rules.md) | A rule above needs its example, its reasoning or the trap table. |
| [errors.md](references/errors.md) | Sentinels, custom error types, `errors.Is` and `errors.AsType`, joining, panics. |
| [concurrency.md](references/concurrency.md) | Worker pools, `errgroup`, channels, shutdown, `sync.Pool`. |
| [project-layout.md](references/project-layout.md) | Module layout, package naming, options pattern, embedding. |
| [tooling.md](references/tooling.md) | Build, format, vet and test commands, modules, the CI gate. |
| [golangci-lint.md](references/golangci-lint.md) | Running `golangci-lint`, its v2 configuration, converting a v1 file. |
| [testing.md](references/testing.md) | Test shape, `t.Cleanup`, `synctest`, parallel subtests, coverage. |
| [table-tests.md](references/table-tests.md) | Table shapes, error cases, subtests, golden files. |
| [go-cmp.md](references/go-cmp.md) | Comparing structs in a test with `cmp.Diff`. |
| [mocks-and-fakes.md](references/mocks-and-fakes.md) | Fakes, stubs, spies, interfaces at the consumer, `httptest`. |
| [integration.md](references/integration.md) | Real databases, containers, build tags, HTTP handler tests. |
| [benchmarks.md](references/benchmarks.md) | Benchmarks, allocation counts, profiles, fuzzing, coverage. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a Go change or a Go review done. |
