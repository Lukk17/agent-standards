---
name: python-patterns
description: Idiomatic Python for production code, covering type hints, error handling, dataclasses, context managers, concurrency choice, and package layout. Use when writing a new Python module, reviewing Python code, adding type hints to a legacy file, refactoring a package layout, or choosing between threads, processes and asyncio. Not for writing tests or pytest configuration, use `python-testing`.
---

# Python Development Patterns

Language-level rules for production Python: how to name things, type them, fail loudly, model data, and lay a package
out. Framework stacks, tool configuration, and the long catalogues live in the reference files listed near the bottom.

Baseline: Python 3.13 or newer, with 3.14 the current release. Every example assumes that floor, so builtin generics,
`X | None`, `match`, and `asyncio.TaskGroup` appear without a compatibility note.

---

### When to activate

- Writing a new Python module, package, or service.
- Reviewing or refactoring existing Python code.
- Adding type hints to an untyped file and choosing how strict to be.
- Deciding between threads, processes, and asyncio for a workload.
- Designing a package layout, its imports, and its public exports.

---

### When not to activate

- Writing tests, fixtures, mocks, or pytest configuration. Use `python-testing`.
- Setting up log formats, metrics, tracing, or the startup readiness banner. Use `observability-and-logging`.
- Applying cross-language design principles such as SOLID, DRY, and naming. Use `coding-standards`.
- Writing training loops, tensor code, or CUDA placement. Use `pytorch-patterns`.
- Deciding blank-line and control-flow layout inside a function body. Use `code-formatter`.
- Profiling a slow endpoint or query before changing it. Use `performance-optimization`.

---

### Write code that explains itself

Names carry the meaning. A reader should not need the body to know what a function returns or what a variable holds.

Pass:

```python
def get_active_users(users: list[User]) -> list[User]:
    return [user for user in users if user.is_active]
```

Fail:

```python
def get_active_users(u):
    return [x for x in u if x.a]
```

---

### Prefer EAFP over LBYL

Ask forgiveness, not permission. Check-then-act duplicates the lookup and opens a race whenever the object can change
between the two statements.

Pass:

```python
try:
    return mapping[key]
except KeyError:
    return default
```

Fail:

```python
if key in mapping:
    return mapping[key]
return default
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

Pass:

```python
def reserve_stock(order_id: OrderId, hold_for: timedelta) -> Reservation:
    """Reserve stock for an order and hold it until the payment window closes.

    Args:
        hold_for: how long the reservation survives, capped at 15 minutes.

    Raises:
        InsufficientStockError: when the warehouse cannot cover the order.
    """
```

Fail:

```python
def reserve_stock(order_id: OrderId, hold_for: timedelta) -> Reservation:
    """Reserve stock.

    Args:
        order_id (OrderId): The order identifier.
        hold_for (timedelta): The hold duration.

    Returns:
        Reservation: The reservation.
    """
```

Best of all, naming and annotations carry it and no docstring is needed:

```python
def reserve_stock_until_payment_window_closes(order_id: OrderId, hold_for: timedelta) -> Reservation: ...
```

---

### Annotate every public signature

Use builtin generics and the union operator. The `typing` aliases `List`, `Dict`, and `Optional` are legacy spellings
that only add an import. Depth on protocols, type aliases, and generics lives in
[references/typing.md](references/typing.md).

Pass:

```python
def process_user(user_id: str, data: dict[str, object], active: bool = True) -> User | None:
    return User(user_id, data) if active else None
```

Fail:

```python
from typing import Any, Dict, Optional

def process_user(user_id, data: Dict[str, Any], active=True) -> Optional[User]:
    return User(user_id, data)
```

---

### Keep `Any` at the system boundary

`Any` switches the type checker off for everything it touches. It is honest at the edge where an untyped library or a
raw payload arrives, and it is a defect inside domain code. Reach for `object`, a `TypeVar`, a `Protocol`, or an
explicit union instead, then narrow once at the boundary.

Pass:

```python
raw: Any = legacy_library.get_result()
config = ReportConfig.model_validate(raw)

def summarise(config: ReportConfig) -> str: ...
```

Fail:

```python
def summarise(config: Any) -> str: ...
```

---

### Raise specific exceptions and chain the cause

Catch the exception you can actually handle, translate it into a domain error, and keep the original traceback with
`from`. A bare `except` swallows `KeyboardInterrupt` and hides the bug you are trying to find.

Pass:

```python
try:
    return Config.from_json(path.read_text())
except json.JSONDecodeError as exc:
    raise ConfigError(f"invalid JSON in config: {path}") from exc
```

Fail:

```python
try:
    return Config.from_json(path.read_text())
except:
    return None
```

Root the whole hierarchy in one application base class, so a caller can catch everything the application raises
without also catching library errors, and the HTTP or CLI boundary has one place to map errors onto responses.

```python
class AppError(Exception): ...
class ValidationError(AppError): ...
class NotFoundError(AppError): ...
```

---

### Release every resource with a context manager

`with` closes the resource on the exception path too. Custom managers, `ExitStack`, and transaction wrappers are in
[references/idioms.md](references/idioms.md).

Pass:

```python
with path.open(encoding="utf-8") as handle:
    return handle.read()
```

Fail:

```python
handle = open(path)
return handle.read()
```

---

### Model data with dataclasses, not loose dicts

A dataclass gives the shape a name, a constructor, equality, and a place to put validation. A dict of strings gives
none of that and defers every typo to runtime.

Pass:

```python
@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

Fail:

```python
user = {"id": "123", "email": "alice@example.com", "created": time.time()}
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

Pass:

```python
async with asyncio.TaskGroup() as group:
    tasks = [group.create_task(fetch(url)) for url in urls]
```

Fail:

```python
with ProcessPoolExecutor() as pool:
    results = list(pool.map(fetch, urls))
```

---

### Lay the package out under src and import absolutely

A `src/` layout stops tests from importing the working directory instead of the installed package. Relative imports
that climb past one level make a module unreadable and unmovable.

Pass:

```python
from myapp.domain.user import User
```

Fail:

```python
from ...domain.user import User
```

```text
src/myapp/__init__.py
src/myapp/domain/user.py
tests/conftest.py
pyproject.toml
```

State the public surface in `__init__.py` with `__all__` and re-export only what callers are meant to use. Everything
absent from it is internal and can be moved without a deprecation.

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
| String built by `+=` in a loop | `"".join(parts)` |

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
| [references/idioms.md](references/idioms.md) | Context managers, decorators, comprehensions, generators, `__slots__` |
| [references/concurrency.md](references/concurrency.md) | Thread pools, process pools, asyncio, cancellation |
| [references/tooling.md](references/tooling.md) | uv, ruff, mypy, pyproject, pre-commit, security scanning |
| [references/fastapi-stack.md](references/fastapi-stack.md) | Optional FastAPI and FastMCP service conventions |

---

### Related skills

- `python-testing` for pytest, fixtures, mocking, and the coverage gate.
- `coding-standards` for the cross-language floor this skill sits on.
- `observability-and-logging` for log discipline, metrics, and the startup readiness log.
- `performance-optimization` for measuring before you optimise.
- `pytorch-patterns` for model and training code.
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
- `ruff check`, `ruff format --check`, and `mypy --strict` all pass.
