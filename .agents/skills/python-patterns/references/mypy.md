# mypy

mypy for types, in strict mode. Open this when setting the type check up, when a third-party package ships no stubs, or when a `# type: ignore` is being added. The typing rules themselves are in [typing.md](typing.md).

---

### Type check in strict mode

Strict mode is the gate. Anything less lets untyped functions through, which is where the bugs a checker exists to
catch actually live.

```bash
mypy --strict src
```

Adopting strict mode on an existing codebase is a per-module migration, not a flag day. Add modules to the strict set
as they are typed, and never widen the setting to make a red build green.

```toml
[tool.mypy]
strict = true
python_version = "3.14"
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
