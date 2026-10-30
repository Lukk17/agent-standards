---
name: python-patterns
description: "Idiomatic Python 3.14 for production code and the pytest suite that proves it, covering type hints, error handling, dataclasses, concurrency choice, package layout, fixtures, mocking boundaries and the coverage gate. Use when the user says \"review this Python module\", \"add type hints to this file\" or \"fix this flaky pytest suite\". Not for training loops and tensor code, use `pytorch-patterns`."
---

# Python Development Patterns

Language-level rules for production Python and the test suite that proves it: how to name things, type them, fail loudly, model data, lay a package out, and test it. The hub carries the rules that decide most reviews, and each reference file carries the depth for one area.

Written for Python 3.14 and pytest 9. Every example assumes them, so builtin generics, `X | None`, `match`, and `asyncio.TaskGroup` appear without a compatibility note.

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

### Rules

1. Name for meaning and annotate every public signature with builtin generics and `X | None`, never `List`, `Dict` or `Optional`.
2. Keep `Any` at the system boundary and narrow it once there. Inside domain code use `object`, a `TypeVar`, a `Protocol` or a union.
3. Catch only what you can handle, translate it to a domain error with `from`, never a bare `except`, and root every error in one `AppError`.
4. Model data crossing a module boundary as a dataclass (`frozen=True, slots=True`), never a loose dict.
5. Pick concurrency from the bottleneck: threads for blocking library I/O, processes for CPU, `asyncio.TaskGroup` for awaitable I/O. One model per process, and the only mix is `asyncio.to_thread` or `run_in_executor` from async code.
6. Lay the package out under `src/`, import absolutely, and state the public surface with `__all__`.
7. Watch every test fail before the code exists. One behaviour per test, named after the outcome, asserted with plain `assert` or `pytest.raises(..., match=...)`.
8. Mock only what you cannot run, patch where the name is used, and pass `autospec=True`. The database is not mocked when a real engine can run.
9. Cover around 90 percent of real logic and 100 percent of critical paths. A failing gate means a missing test, never a lower threshold, and only generated output is excluded.
10. Run the whole suite from the project root before calling a change good, and avoid the legal-but-wrong traps listed in the core rules reference.
11. The startup readiness log belongs to `observability-and-logging`. Do not restate it or invent a local variant.

---

### Docstrings

Docstrings follow the Doc Comments rules in `coding-standards`. Python delta: use the Google `Args:`, `Returns:` and `Raises:` sections, and treat `Raises:` as the contract slot, written for every exception a caller can act on, because nothing about raising appears in a Python signature. Never restate a type an annotation already declares.

---

### Reference files

| Open this | When |
| --- | --- |
| [references/core-rules.md](references/core-rules.md) | A hub rule needs its BAD and GOOD example, its full reasoning, or the trap table |
| [references/typing.md](references/typing.md) | Protocols, type aliases, generics, `TypeVar`, narrowing |
| [references/idioms.md](references/idioms.md) | EAFP, context managers, decorators, comprehensions, generators, `__slots__` |
| [references/concurrency.md](references/concurrency.md) | Thread pools, process pools, asyncio, cancellation |
| [references/tooling.md](references/tooling.md) | uv, ruff, mypy, the `src` tree, pre-commit, security scanning |
| [references/fastapi-stack.md](references/fastapi-stack.md) | Optional FastAPI and FastMCP service conventions |
| [references/testing.md](references/testing.md) | Test shape and naming, parametrization, isolation, async tests, markers |
| [references/fixtures-and-mocking.md](references/fixtures-and-mocking.md) | Fixture scopes, conftest, autouse, patching, autospec |
| [references/pytest-config.md](references/pytest-config.md) | pyproject configuration, markers, CLI flags, coverage, CI |
| [references/integration-tests.md](references/integration-tests.md) | Suite layout, FastAPI clients, database sessions, test classes |

---

### Related skills

- `coding-standards` for the cross-language floor this skill sits on.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `observability-and-logging` for log discipline, metrics, and the startup readiness log.
- `performance-optimization` for measuring before you optimise.
- `pytorch-patterns` for model and training code.
- `e2e-testing` for browser journeys and the flaky-test policy.
- `build-dependency-management` for how dependency versions are admitted and pinned.

---

### Checklist

- Every public function and method has annotated parameters and a return type.
- No `Any` outside a boundary adapter, and every boundary narrows it immediately.
- Docstrings follow `coding-standards`, in the Google `Args:` / `Returns:` / `Raises:` form.
- `Raises:` documents every exception a caller can act on.
- Exceptions are specific, chained with `from`, and rooted in one application base class.
- No bare `except`, no silent `pass`, no `return None` standing in for a failure.
- Every file, socket, and transaction is acquired inside a `with`.
- Data crossing a module boundary is a dataclass or a model, not a raw dict.
- The concurrency model matches the bottleneck, one model per process, blocking calls offloaded from async to threads.
- The package sits under `src/`, imports are absolute, and `__all__` states the public surface.
- Every new behaviour has a test that was seen to fail before the code was written.
- Only genuinely external services are mocked, and coverage of real logic is around 90 percent.
- `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest` all pass from the project root.
