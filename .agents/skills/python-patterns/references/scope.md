# Scope

Companion reference for the [python-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing a new Python module, package, or service.
- The user says "review this Python module", "add type hints to this file", "threads, processes or asyncio", "write tests for this", "fix this flaky pytest suite", or "mock this external API".
- Reviewing or refactoring existing Python code.
- Adding type hints to an untyped file and choosing how strict to be.
- Deciding between threads, processes, and asyncio for a workload.
- Designing a package layout, its imports, and its public exports.
- Writing pytest tests, fixtures, or mocks, or raising coverage on a module.

---

### When not to activate

- Applying cross-language design principles such as SOLID, DRY, and naming. Use `coding-standards`.
- Applying the language-neutral red-green-refactor loop and the test pyramid. Use `tdd-workflow`.
- Setting up log formats, metrics, tracing, or the startup readiness banner. Use `observability-and-logging`.
- Writing training loops, tensor code, or CUDA placement. Use `pytorch-patterns`.
- Driving a browser through a user journey. Use `e2e-testing`.
- Deciding blank-line and control-flow layout inside a function body. Use `code-formatter`.
- Profiling a slow endpoint or query before changing it. Use `performance-optimization`.

---

### Related skills

- `coding-standards` for the cross-language floor this skill sits on.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `observability-and-logging` for log discipline, metrics, and the startup readiness log.
- `performance-optimization` for measuring before you optimise.
- `pytorch-patterns` for model and training code.
- `e2e-testing` for browser journeys and the flaky-test policy.
- `build-dependency-management` for how dependency versions are admitted and pinned.
