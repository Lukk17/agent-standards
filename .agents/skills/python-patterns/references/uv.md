# uv

uv for the environment, the lock file and the pins a Python project carries in `pyproject.toml`. Open this when setting a project up, adding a dependency, or when a build is not reproducible.

Written for Python 3.14.

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

### Pin exact versions, and let the lock file pin the rest

`build-dependency-management` owns the version policy: pin exact versions so a clean checkout builds the same artifacts
tomorrow, because a range turns every build into a different build. Every direct dependency in `pyproject.toml` carries
an exact `==` pin, and `uv.lock` pins every transitive dependency on top of it. A bump is a deliberate edit to one line.

```toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.14"
dependencies = [
    "fastapi==0.141.1",
    "pydantic==2.13.5",
    "pydantic-settings==2.15.0",
]

[dependency-groups]
dev = [
    "httpx==0.28.1",
    "mypy==2.3.1",
    "pytest==9.1.1",
    "pytest-asyncio==1.4.0",
    "pytest-cov==7.1.0",
    "ruff==0.16.9",
]
```

The pins show the exact-pin form, not a recommended release. Replace each with the release you admit when you copy the file, and never loosen one into a range.

Pytest configuration is deliberately absent from this file. It belongs to [pytest-config.md](pytest-config.md),
which owns `[tool.pytest.ini_options]`, the marker registry, and the coverage gate. The `[tool.ruff]` blocks of the same file are in
[ruff.md](ruff.md), and `[tool.mypy]` is in [mypy.md](mypy.md).
