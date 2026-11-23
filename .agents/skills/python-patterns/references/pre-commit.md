# pre-commit

A pre-commit hook that runs the lint, format and type checks before a commit. Open this when wiring the checks into a clone. The checks themselves are in [ruff.md](ruff.md) and [mypy.md](mypy.md).

---

### Wire the checks into pre-commit

The hook catches the same failures locally that CI would catch minutes later.

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: ""
    hooks:
      - id: ruff-check
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: ""
    hooks:
      - id: mypy
        args: [--strict]
```

Leave each `rev` empty in the draft and fill them from the current tags:

```bash
pre-commit autoupdate
```

A `rev` copied out of a document is stale the week after the document is written, which is why none is written here.

Install the hook once per clone:

```bash
pre-commit install
```
