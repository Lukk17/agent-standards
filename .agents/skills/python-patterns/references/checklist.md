# Python Checklist

Run it before calling a Python change or a Python review done. The rules behind each item are in [SKILL.md](../SKILL.md), and the test checklist is at the end of [testing.md](testing.md).

- [ ] Every public function and method has annotated parameters and a return type.
- [ ] No `Any` outside a boundary adapter, and every boundary narrows it immediately.
- [ ] Docstrings follow `coding-standards`, in the Google `Args:` / `Returns:` / `Raises:` form.
- [ ] `Raises:` documents every exception a caller can act on.
- [ ] Exceptions are specific, chained with `from`, and rooted in one application base class.
- [ ] No bare `except`, no silent `pass`, no `return None` standing in for a failure.
- [ ] Every file, socket, and transaction is acquired inside a `with`.
- [ ] Data crossing a module boundary is a dataclass or a model, not a raw dict.
- [ ] The concurrency model matches the bottleneck, one model per process, blocking calls offloaded from async to threads.
- [ ] The package sits under `src/`, imports are absolute, and `__all__` states the public surface.
- [ ] Every new behaviour has a test that was seen to fail before the code was written.
- [ ] Only genuinely external services are mocked, and coverage of real logic is around 90 percent.
- [ ] `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest` all pass from the project root.
