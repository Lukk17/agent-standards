# Python Core Rules in Depth

The BAD and GOOD examples, the reasoning, and the trap table behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for Python 3.14 and pytest 9.

---

### Contents

- Name and annotate every public signature
- Docstrings
- Raise specific exceptions and chain the cause
- Model data with dataclasses, not loose dicts
- Pick the concurrency model from the bottleneck
- Lay the package out under src and import absolutely
- Test it, and watch the test fail first
- Avoid the classic traps
- Startup readiness log

---

### Name and annotate every public signature

Names carry the meaning, and a reader should not need the body to know what a function returns. Annotate with builtin
generics and the union operator: the `typing` aliases `List`, `Dict`, and `Optional` are legacy spellings that only
add an import. Keep `Any` at the system boundary, where an untyped library or a raw payload arrives, and narrow it
once there. Inside domain code it switches the type checker off for everything it touches, and `object`, a `TypeVar`,
a `Protocol`, or an explicit union says the same thing without the blind spot. Depth on protocols, type aliases, and
generics is in [references/typing.md](typing.md).

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

### Docstrings

Docstrings follow the Doc Comments rules in `coding-standards`. Python delta: use the Google `Args:`, `Returns:` and `Raises:` sections, and treat `Raises:` as the contract slot, written for every exception a caller can act on, because nothing about raising appears in a Python signature. Never restate a type an annotation already declares.

```python
def reserve_stock(order_id: OrderId, hold_for: timedelta) -> Reservation:
    """Reserve stock for an order and hold it until the payment window closes.

    Args:
        hold_for: how long the reservation survives, capped at 15 minutes.

    Raises:
        InsufficientStockError: when the warehouse cannot cover the order.
    """
```

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

Match the tool to what the work is waiting on, then stop. Running independent models side by side in one process is
where deadlocks and starved pools come from. The one sanctioned mix is async code handing a blocking call to a thread
with `asyncio.to_thread` or `run_in_executor`, so the event loop never stalls. Full examples are in
[references/concurrency.md](concurrency.md).

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
`pyproject.toml` beside it are in [references/tooling.md](tooling.md).

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

Mock only what you cannot run. A third-party payment API or an email gateway is fair, the database is not, when a
containerised real engine or a transactional session fixture on it will exercise the real query, and mocking the thing
under test only proves the mock was called. Patch where the name is used, not where it is defined, and pass
`autospec=True`.

Cover around 90 percent of the real logic and 100 percent of the critical paths. A failing coverage gate is a signal
to add the missing test, never to lower the threshold or add an exclusion: generated output such as protobuf stubs is
a legitimate exclusion, a hand-written module that is awkward to test is not.

```bash
pytest --cov=mypackage --cov-report=term-missing
```

Run the whole suite from the project root before calling a change good. Test shape, parametrization, isolation, async
mode, markers, fixtures, and integration layout are in [references/testing.md](testing.md).

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
