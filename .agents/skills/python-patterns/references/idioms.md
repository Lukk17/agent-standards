# Python Idioms Catalogue

Context managers, decorators, comprehensions, dataclass validation, named tuples, and the memory tricks that pay for
themselves. Open this when the hub rule points here for a fuller example than the pass and fail pair it shows.

---

### Keep side effects out of import time

Importing a module must not open sockets, read files, or mutate global state. Put the work in a function the caller
invokes, so tests and tooling can import the module without paying for it and without a hidden ordering dependency
between imports.

Pass:

```python
def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(name)s %(levelname)s %(message)s")
```

Fail:

```python
import some_module

some_module.setup()
```

The same applies to a module-level `connect()`, a `requests.get` at import time, and a top-level `sys.path` edit.

---

### Comprehend simply, generate lazily

A comprehension is for one filter and one transform. Anything more belongs in a named function, where the reader can
follow the steps and the debugger can stop between them. Feed an aggregate from a generator expression so the
intermediate list is never built.

Pass:

```python
active_names = [user.name for user in users if user.is_active]
total = sum(x * x for x in range(1_000_000))
```

Fail:

```python
result = [transform(x) * 2 for x in items if x > 0 if x % 2 == 0 if x not in seen]
total = sum([x * x for x in range(1_000_000)])
```

---

### Write a context manager with `@contextmanager`

For a manager with no state beyond the block, the generator form is shorter than a class and impossible to get wrong.

```python
@contextmanager
def timed(name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        logger.info("%s took %.4fs", name, time.perf_counter() - start)
```

Put the `yield` inside a `try`/`finally` whenever the teardown must run on the exception path, which is nearly always.

---

### Write a context manager class when it owns state

A class earns its keep when the manager exposes something to the block or has to inspect the exception.

```python
class Transaction:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def __enter__(self) -> Connection:
        self._connection.begin()
        return self._connection

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> bool:
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        return False
```

Returning `False` from `__exit__` lets the exception propagate. Returning `True` swallows it, which is almost never
what you want.

---

### Stack optional managers with `ExitStack`

`ExitStack` handles a variable number of resources without nesting `with` statements or writing a recursive helper.

```python
def merge(paths: list[Path]) -> str:
    with ExitStack() as stack:
        handles = [stack.enter_context(path.open(encoding="utf-8")) for path in paths]
        return "".join(handle.read() for handle in handles)
```

---

### Preserve metadata in every decorator

Without `functools.wraps` the wrapped function loses its name, docstring, and annotations, which breaks introspection,
pytest reporting, and the type checker.

Pass:

```python
def retry[**P, R](attempts: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except TransientError:
                    if attempt == attempts:
                        raise
            raise AssertionError("unreachable")

        return wrapper

    return decorate
```

Fail:

```python
def retry(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

---

### Validate a dataclass in `__post_init__`

`__post_init__` runs after the generated `__init__` assigns the fields, so it is the one place an invariant can be
enforced without writing a constructor by hand.

```python
@dataclass(frozen=True, slots=True)
class Account:
    email: str
    balance_cents: int

    def __post_init__(self) -> None:
        if "@" not in self.email:
            raise ValueError(f"invalid email: {self.email}")
        if self.balance_cents < 0:
            raise ValueError("balance cannot be negative")
```

Use `field(default_factory=...)` for any mutable default. A bare `list` default on a dataclass raises at class
creation, which is the language stopping you from repeating the mutable-default bug.

---

### Reach for `NamedTuple` only when tuple behaviour is wanted

A `NamedTuple` is a tuple: it unpacks, indexes, and compares positionally. That is right for a coordinate or a small
return value, and wrong for a domain entity, where positional equality is a trap.

```python
class Point(NamedTuple):
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)
```

For everything else use a frozen dataclass, which compares by field and refuses to be unpacked by accident.

---

### Yield from a generator instead of returning a list

A generator holds one item at a time. Returning a list of every line in a large file is the difference between
constant memory and a process the kernel kills.

Pass:

```python
def read_lines(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\n")
```

Fail:

```python
def read_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        return [line.rstrip("\n") for line in handle]
```

A generator that owns a file must be fully consumed or explicitly closed, so keep the `with` inside the generator as
shown rather than passing an already-open handle in.

---

### Add `slots=True` when instances are many

`slots` removes the per-instance `__dict__`, which cuts memory noticeably once a type is instantiated in the
thousands. On a dataclass it is one keyword.

```python
@dataclass(slots=True)
class Point:
    x: float
    y: float
```

The cost is that instances gain no ad-hoc attributes and multiple inheritance gets fussier, so apply it to leaf value
types rather than to every class.

---

### Build strings with `join`, not `+=`

Repeated concatenation copies the whole string on every iteration, so the loop is quadratic in the output length.

Pass:

```python
report = "".join(f"{row.name}: {row.total}\n" for row in rows)
```

Fail:

```python
report = ""
for row in rows:
    report += f"{row.name}: {row.total}\n"
```

For interleaved writes that are not a single expression, use `io.StringIO` and read `getvalue()` at the end.
