# Python Tooling

The tree a Python project sits in and the toolchain it carries: the `src` layout, uv for environments and locking,
ruff for lint and format, mypy for types, and a pre-commit hook that runs them. Open this when setting a project up
or when a check is missing in CI.

Baseline: Python 3.13 or newer, with 3.14 the current release.

---

### Lay the package out under src

A `src/` layout stops tests from importing the working directory instead of the installed package, which is how a
suite passes against files that were never packaged.

```text
src/myapp/__init__.py
src/myapp/domain/user.py
tests/conftest.py
pyproject.toml
```

State the public surface in `__init__.py` with `__all__` and re-export only what callers are meant to use. Everything
absent from it is internal and can be moved without a deprecation.

```python
from myapp.domain.user import User

__all__ = ["User"]
```

Imports are absolute everywhere. A relative import that climbs past one level, `from ...domain.user import User`,
makes the module unreadable and unmovable.

---

### Use uv for the environment and the lock file

uv replaces pip, virtualenv, and pip-tools with one tool that resolves and installs from `pyproject.toml` and records
the result in `uv.lock`.

Create the environment:

```bash
uv venv
```

Install the project and its dependency groups from the lock file:

```bash
uv sync
```

Add a dependency, which updates both `pyproject.toml` and the lock file:

```bash
uv add httpx
```

Run a command inside the project environment without activating it:

```bash
uv run pytest
```

Commit `uv.lock`. It is the single record of the exact versions a build used, which is what makes a build
reproducible.

---

### Pin a floor, let the lock file pin the version

Name a version in `pyproject.toml` only where a major release changed the API you rely on. Everything else resolves to
the newest compatible release and is pinned exactly in `uv.lock`. A dependency list full of patch-level pins goes
stale within a month and tells a reader nothing about what the code actually needs.

```toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi",
    "pydantic>=2",
    "pydantic-settings>=2",
]

[dependency-groups]
dev = [
    "httpx",
    "mypy",
    "pytest",
    "pytest-asyncio>=1",
    "pytest-cov",
    "ruff",
]

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "A"]

[tool.mypy]
strict = true
python_version = "3.13"
```

`pydantic>=2` and `pytest-asyncio>=1` are floors because each of those majors was a rewrite. `fastapi`, `ruff`, and
`mypy` carry no floor because the project wants whatever is current.

Pytest configuration is deliberately absent from this file. It belongs to [pytest-config.md](pytest-config.md),
which owns `[tool.pytest.ini_options]`, the marker registry, and the coverage gate.

---

### Lint and format with ruff

ruff replaces black, isort, flake8, and pylint with one binary. Run the linter and the formatter as separate steps so
a formatting-only diff never hides a lint failure.

Check for lint violations:

```bash
ruff check .
```

Apply the import ordering and other safe fixes:

```bash
ruff check --fix .
```

Format the tree:

```bash
ruff format .
```

In CI, use the check-only form so the job fails instead of rewriting files:

```bash
ruff format --check .
```

---

### Type check in strict mode

Strict mode is the gate. Anything less lets untyped functions through, which is where the bugs a checker exists to
catch actually live.

```bash
mypy --strict src
```

Adopting strict mode on an existing codebase is a per-module migration, not a flag day. Add modules to the strict set
as they are typed, and never widen the setting to make a red build green.

---

### Scan dependencies and code for known problems

Audit the resolved dependency set against the advisory database:

```bash
uv run pip-audit
```

Run the static security linter over first-party code:

```bash
uv run bandit -r src
```

ruff's `S` rule set already covers much of what bandit reports, so a project that enables `S` can treat bandit as a
second opinion rather than a required gate.

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
