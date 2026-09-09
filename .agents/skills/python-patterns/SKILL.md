---
name: python-patterns
description: Idiomatic Python for production code and the pytest suite that proves it, covering type hints, error handling, dataclasses, context managers, concurrency choice, package layout, fixtures, mocking boundaries, and the coverage gate. Use when writing a new Python module, reviewing Python code, adding type hints to a legacy file, choosing between threads, processes and asyncio, writing tests for new code, fixing a flaky pytest suite, or mocking an external API. Not for training loops, tensor code, and CUDA placement, use `pytorch-patterns`.
---

# Python Development Patterns

Language-level rules for production Python and the test suite that proves it: how to name things, type them, fail
loudly, model data, lay a package out, and test it. The hub carries the rules that decide most reviews, and each
reference file carries the depth for one area.

Baseline: Python 3.13 or newer, with 3.14 the current release, and the current stable pytest. Every example assumes
that floor, so builtin generics, `X | None`, `match`, and `asyncio.TaskGroup` appear without a compatibility note.

---

### When to activate

- Writing a new Python module, package, or service.
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

### Name and annotate every public signature

Names carry the meaning, and a reader should not need the body to know what a function returns. Annotate with builtin
generics and the union operator: the `typing` aliases `List`, `Dict`, and `Optional` are legacy spellings that only
add an import. Keep `Any` at the system boundary, where an untyped library or a raw payload arrives, and narrow it
once there. Inside domain code it switches the type checker off for everything it touches, and `object`, a `TypeVar`,
a `Protocol`, or an explicit union says the same thing without the blind spot. Depth on protocols, type aliases, and
generics is in [references/typing.md](references/typing.md).

```python
# BAD
from typing import Any, Dict, Optional

def process(u, data: Dict[str, Any], a=True) -> Optional[User]:
    return User(u, data)

# GOOD
def process_user(user_id: str, data: dict[str, object], active: bool = True) -> User | None:
    return User(user_id, data) if active else None

# GOOD. Any is honest at the edge, narrowed once, and never seen again.
raw: Any = legacy_library.get_result()
config = ReportConfig.model_validate(raw)
```

---

### Docstrings: default to none

A docstring is usually a sign that the code failed to explain itself. Before writing one, extract the unclear block
into a well-named function, rename the arguments so they carry their own meaning, and tighten the types. Do that first
and most docstrings have nothing left to say, which is the outcome you want. Code that explains itself cannot go
stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every entry under `Args:`,
`Returns:` or `Raises:` is capped at one line and only appears when it genuinely adds something: if the entry does not
fit on a single line, shorten it or drop it. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `Args:` only when the name and the annotation do not already convey it, meaning units, nullability, a valid range,
   or who owns the argument afterwards. `user_id: The user identifier` is noise, delete it, and never restate a type
   the annotation already declares.
3. `Returns:` only when it is non-obvious.
4. `Raises:` always, for every exception a caller can act on. Python puts nothing about raising in the signature, so
   this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on an entry line has no exception at all: shorten it or
delete it.

```python
# GOOD. One sentence, then only what the signature cannot carry, one line per entry.
def reserve_stock(order_id: OrderId, hold_for: timedelta) -> Reservation:
    """Reserve stock for an order and hold it until the payment window closes.

    Args:
        hold_for: how long the reservation survives, capped at 15 minutes.

    Raises:
        InsufficientStockError: when the warehouse cannot cover the order.
    """
```

The failing shape is the same function documented as `Reserve stock.` with an `Args:` block restating both
annotations and a `Returns:` line saying `Reservation: The reservation.` Best of all, naming and annotations carry
it and no docstring is needed at all.

---

### Raise specific exceptions and chain the cause

Catch the exception you can actually handle, translate it into a domain error, and keep the original traceback with
`from`. A bare `except` swallows `KeyboardInterrupt` and hides the bug you are trying to find.

```python
# BAD
try:
    return Config.from_json(path.read_text())
except:
    return None

# GOOD
try:
    return Config.from_json(path.read_text())
except json.JSONDecodeError as exc:
    raise ConfigError(f"invalid JSON in config: {path}") from exc
```

Root the whole hierarchy in one application base class, so `ValidationError` and `NotFoundError` both subclass a
single `AppError`. A caller can then catch everything the application raises without also catching library errors,
and the HTTP or CLI boundary has one place to map errors onto responses.

---

### Model data with dataclasses, not loose dicts

A dataclass gives the shape a name, a constructor, equality, and a place to put validation. A dict of strings gives
none of that and defers every typo to runtime.

```python
# BAD
user = {"id": "123", "email": "alice@example.com", "created": time.time()}

# GOOD
@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

---

### Pick the concurrency model from the bottleneck

Match the tool to what the work is waiting on, then stop. Mixing models in one process is where deadlocks and starved
pools come from. Full examples are in [references/concurrency.md](references/concurrency.md).

| Bottleneck | Tool |
| --- | --- |
| Blocking I/O in library code you do not control | `concurrent.futures.ThreadPoolExecutor` |
| CPU-bound computation | `concurrent.futures.ProcessPoolExecutor` |
| Many awaitable I/O calls in async code | `asyncio.TaskGroup` |

```python
# BAD
with ProcessPoolExecutor() as pool:
    results = list(pool.map(fetch, urls))

# GOOD
async with asyncio.TaskGroup() as group:
    tasks = [group.create_task(fetch(url)) for url in urls]
```

---

### Lay the package out under src and import absolutely

A `src/` layout stops tests from importing the working directory instead of the installed package, and a relative
import that climbs past one level makes a module unreadable and unmovable. State the public surface in `__init__.py`
with `__all__`: everything absent from it is internal and can be moved without a deprecation. The tree and the
`pyproject.toml` beside it are in [references/tooling.md](references/tooling.md).

```python
# BAD
from ...domain.user import User

# GOOD
from myapp.domain.user import User
```

---

### Test it, and watch the test fail first

The failing run is the only evidence a test can fail at all, so a test written after the code passes on the first run
and has never shown it would catch the bug. Give each test one behaviour, name it after the outcome rather than the
function, and assert with plain `assert` or `pytest.raises(..., match=...)`.

```python
# BAD
def test_login():
    assert True

# GOOD
def test_login_with_expired_token_returns_401(client):
    response = client.get("/me", headers=expired_token_header())

    assert response.status_code == 401
```

Mock only what you cannot run. A third-party payment API or an email gateway is fair, the database is not when an
in-memory engine or a transactional session fixture will exercise the real query, and mocking the thing under test
only proves the mock was called. Patch where the name is used, not where it is defined, and pass `autospec=True`.

Cover around 90 percent of the real logic and 100 percent of the critical paths. A failing coverage gate is a signal
to add the missing test, never to lower the threshold or add an exclusion: generated output such as protobuf stubs is
a legitimate exclusion, a hand-written module that is awkward to test is not.

```bash
pytest --cov=mypackage --cov-report=term-missing
```

Run the whole suite from the project root before calling a change good. Test shape, parametrization, isolation, async
mode, markers, fixtures, and integration layout are in [references/testing.md](references/testing.md).

---

### Avoid the classic traps

Each of these is legal Python that does something other than what it looks like.

| Trap | Do instead |
| --- | --- |
| `def f(items=[])` mutable default | `def f(items: list[int] \| None = None)` then build inside |
| `type(obj) == list` | `isinstance(obj, list)` |
| `if value == None` | `if value is None` |
| `from os.path import *` | Import the names you use |
| `except:` with `pass` | Catch the specific exception and log or re-raise |
| `if key in mapping` before reading it | `try` the read and catch `KeyError`, which is one lookup and no race |
| `open(path)` with no `with` | `with path.open(encoding="utf-8") as handle` |
| String built by `+=` in a loop | `"".join(parts)` |
| `time.sleep` in a test to wait for something | A fixture, a fake clock, or an explicit await |

---

### Startup readiness log

The banner, the section order, the 2-second probe timeout, and the `<url> [Connected|Warning|FAILED]` result format
are one convention shared by every language. It lives in `observability-and-logging`, including the Python hook per
framework and the rule that the whole block is emitted in a single log call with a leading newline. Do not restate it
here and do not invent a local variant.

---

### Reference files

| Open this | For |
| --- | --- |
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
- Docstrings are absent, or one sentence plus only the entries the signature cannot carry.
- `Raises:` documents every exception a caller can act on.
- Exceptions are specific, chained with `from`, and rooted in one application base class.
- No bare `except`, no silent `pass`, no `return None` standing in for a failure.
- Every file, socket, and transaction is acquired inside a `with`.
- Data crossing a module boundary is a dataclass or a model, not a raw dict.
- The concurrency model matches the bottleneck and only one model is used per process.
- The package sits under `src/`, imports are absolute, and `__all__` states the public surface.
- Every new behaviour has a test that was seen to fail before the code was written.
- Only genuinely external services are mocked, and coverage of real logic is around 90 percent.
- `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest` all pass from the project root.
