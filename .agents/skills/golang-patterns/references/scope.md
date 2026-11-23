# Scope

Companion reference for the [golang-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

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

### Related skills

- `coding-standards` for the cross-language floor this skill sits on.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `observability-and-logging` for slog discipline, metrics, and the startup readiness log.
- `api-design` for the shape of the HTTP or gRPC contract a Go service serves.
- `performance-optimization` for what to do with a benchmark once you have one.
- `docker-patterns` for building and shipping the resulting binary.
