# Python Typing Depth

Protocols, aliases, generics, and narrowing for code that has to pass `mypy --strict`. Open this when a signature
needs more than a builtin generic, or when the checker rejects something that looks correct.

Baseline: Python 3.13 or newer, so PEP 695 type parameter syntax and the `type` statement are available.

---

### Declare an alias with the `type` statement

The `type` statement creates a lazily evaluated alias, so a forward reference inside it needs no quoting and no
`from __future__ import annotations`.

```python
type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

def parse_json(data: str) -> JSON:
    return json.loads(data)
```

Reserve an alias for a shape that appears in three or more signatures. One-off aliases hide the type instead of
naming it.

---

### Use PEP 695 syntax for generics

The type parameter list on the function or class removes the separate `TypeVar` declaration and scopes the variable
where it is used.

```python
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None

class Repository[T]:
    def __init__(self, rows: list[T]) -> None:
        self._rows = rows

    def all(self) -> list[T]:
        return list(self._rows)
```

Bound a parameter when the body calls a method on it, so the checker verifies the call site rather than the body.

```python
def largest[T: (int, float)](values: list[T]) -> T:
    return max(values)
```

---

### Describe a shape with a Protocol, not a base class

A protocol types the shape a function needs without forcing the caller's class to inherit anything. Prefer it to an
abstract base class whenever the implementations live outside your package.

```python
class Renderable(Protocol):
    def render(self) -> str: ...

def render_all(items: list[Renderable]) -> str:
    return "\n".join(item.render() for item in items)
```

Add `@runtime_checkable` only when an `isinstance` check is genuinely needed. It checks method names, not signatures,
so it proves less than it appears to.

---

### Narrow with a TypeGuard when the checker cannot follow

An ordinary `bool` return tells the checker nothing. `TypeIs` narrows in both branches, `TypeGuard` narrows only the
positive branch.

```python
def is_str_list(values: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(value, str) for value in values)

def join(values: list[object]) -> str:
    if is_str_list(values):
        return ", ".join(values)
    raise TypeError("expected a list of strings")
```

---

### Prefer a discriminated union to a bag of optional fields

A union of small models plus a literal tag lets the checker prove which branch is live. A single class with six
optional fields defers every combination to runtime.

Pass:

```python
@dataclass(frozen=True)
class CardPayment:
    kind: Literal["card"]
    last4: str

@dataclass(frozen=True)
class TransferPayment:
    kind: Literal["transfer"]
    iban: str

type Payment = CardPayment | TransferPayment

def describe(payment: Payment) -> str:
    match payment:
        case CardPayment(last4=last4):
            return f"card ending {last4}"
        case TransferPayment(iban=iban):
            return f"transfer to {iban}"
```

Fail:

```python
@dataclass
class Payment:
    kind: str
    last4: str | None = None
    iban: str | None = None
```

---

### Type the callable, not just `Callable`

A bare `Callable` erases the arguments. Spell the signature so a wrong call site fails the check rather than the
production request.

```python
Handler = Callable[[Request], Awaitable[Response]]

def register(path: str, handler: Handler) -> None: ...
```

For a decorator that must preserve the wrapped signature, use `ParamSpec`.

```python
def timed[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.debug("%s took %.4fs", func.__name__, time.perf_counter() - start)

    return wrapper
```

---

### Make the checker strict and keep it that way

Run `mypy --strict` as a CI gate. When a third-party package ships no stubs, silence it once in configuration rather
than sprinkling `# type: ignore` through the code.

```toml
[[tool.mypy.overrides]]
module = ["untyped_vendor.*"]
ignore_missing_imports = true
```

Every remaining `# type: ignore` carries a specific error code, so it stops suppressing errors it was never meant to
cover.

```python
value = legacy.call()  # type: ignore[no-any-return]
```
