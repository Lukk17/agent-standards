---
name: python-patterns
description: 'Python 3.14 patterns and tests: type hints, errors, dataclasses, concurrency, mocking. Use when the user says "review this Python module" or "fix this flaky pytest suite". Not for tensor code, use `pytorch-patterns`.'
metadata:
  version: "1.1.0"
---

# Python Development Patterns

Language-level rules for production Python and the test suite that proves it: how to name things, type them, fail loudly, model data, lay a package out, and test it.

Written for Python 3.14 and pytest 9.

---

### When not to activate

- Applying cross-language design principles such as SOLID, DRY, and naming, use `coding-standards`.
- Deciding blank-line and control-flow layout inside a function body, use `code-formatter`.
- Writing training loops, tensor code, or CUDA placement, use `pytorch-patterns`.

---

### Rules

1. Name for meaning and annotate every public signature with builtin generics and `X | None`, never `List`, `Dict` or `Optional`.
2. Keep `Any` at the system boundary and narrow it once there.
3. Catch only what you can handle, translate it to a domain error with `from`, never a bare `except`, and root every error in one `AppError`.
4. Model data crossing a module boundary as a dataclass (`frozen=True, slots=True`), never a loose dict.
5. Pick concurrency from the bottleneck: threads for blocking library I/O, processes for CPU, `asyncio.TaskGroup` for awaitable I/O, and one model per process.
6. Lay the package out under `src/`, import absolutely, and state the public surface with `__all__`.
7. Watch every test fail before the code exists. One behaviour per test, named after the outcome, with an expected error asserted by type and message.
8. Mock only what you cannot run, patch where the name is used, and pass `autospec=True`. The database is not mocked when a real engine can run.
9. Cover around 90 percent of real logic and 100 percent of critical paths. A failing gate means a missing test, never a lower threshold.
10. Run the whole suite from the project root before calling a change good, and avoid the legal-but-wrong traps listed in the core rules reference.
11. The startup readiness log belongs to `observability-and-logging`. Do not restate it or invent a local variant.
12. One job per module: a script is a thin command-line entry over pure, separately tested helper modules, and no module carries a long comment block.
13. Docstrings follow the Doc Comments rules in `coding-standards`, in the Google `Args:`, `Returns:` and `Raises:` form, with `Raises:` for every exception a caller can act on.

---

### Reference files

| Open this | When |
| --- | --- |
| [core-rules.md](references/core-rules.md) | A rule above needs its example or its reasoning. |
| [typing.md](references/typing.md) | Protocols, type aliases, generics, narrowing. |
| [idioms.md](references/idioms.md) | EAFP, context managers, decorators, generators, `__slots__`. |
| [concurrency.md](references/concurrency.md) | Thread pools, process pools, asyncio, cancellation. |
| [uv.md](references/uv.md) | Environments, the lock file, exact pins. |
| [ruff.md](references/ruff.md) | Linting and formatting. |
| [mypy.md](references/mypy.md) | Strict type checking, missing stubs. |
| [security-scanning.md](references/security-scanning.md) | Auditing dependencies and code. |
| [pre-commit.md](references/pre-commit.md) | Running the checks before a commit. |
| [fastapi.md](references/fastapi.md) | A FastAPI service and its tests. |
| [pydantic-settings.md](references/pydantic-settings.md) | Typed settings from the environment. |
| [sqlalchemy-and-alembic.md](references/sqlalchemy-and-alembic.md) | Sessions, migrations, a rollback fixture. |
| [testing.md](references/testing.md) | Test shape, naming, parametrization, async tests. |
| [fixtures-and-mocking.md](references/fixtures-and-mocking.md) | Fixtures, conftest, patching, autospec. |
| [pytest-config.md](references/pytest-config.md) | pytest configuration, markers, flags, coverage, CI. |
| [integration-tests.md](references/integration-tests.md) | Suite layout, test classes, the real database engine. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a Python change or review done. |
