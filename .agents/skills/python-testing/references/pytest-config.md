# pytest Configuration and Command Line

The one configuration block a project needs, the markers that go with it, and the flags worth knowing during a
debugging session. Open this when setting a project up or when a run needs narrowing.

---

### Configure pytest in pyproject.toml

One file, one block. A separate `pytest.ini` or `setup.cfg` splits the project's configuration across files that then
disagree with each other.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=mypackage",
    "--cov-report=term-missing",
]
markers = [
    "slow: takes more than a second",
    "integration: needs a real dependency such as a database or a broker",
    "unit: pure in-process logic",
]
```

`--strict-markers` turns a typo in a marker name into an error instead of a silently unregistered marker.
`--strict-config` does the same for an unknown configuration key.

`--disable-warnings` is deliberately absent. It hides the deprecation that breaks the suite at the next upgrade, and
the noise it suppresses is the warning you were meant to fix. Filter a specific known warning instead:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error", "ignore:legacy transport:DeprecationWarning:vendor_lib"]
```

Turning warnings into errors with `"error"` as the first entry is the stronger position: a new warning fails the
build while it is still cheap to fix.

---

### Coverage settings live with coverage, not in addopts

Threshold and exclusion belong in the coverage configuration, so a developer running one file locally does not fail
the gate.

```toml
[tool.coverage.run]
branch = true
source = ["src/mypackage"]

[tool.coverage.report]
fail_under = 90
show_missing = true
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError", "@overload"]
```

`exclude_also` is for lines that cannot execute, not for logic that is awkward to test. Adding a hand-written module
here to make the gate pass is the failure the gate exists to catch.

---

### Selecting what to run

Run the whole suite, which is the command that decides whether a change is good:

```bash
pytest
```

Run one file while debugging:

```bash
pytest tests/test_users.py
```

Run one test:

```bash
pytest tests/test_users.py::test_create_user_returns_201
```

Select by name substring across the suite:

```bash
pytest -k "user and not admin"
```

Select by marker:

```bash
pytest -m "not slow"
```

Combine markers with the same boolean syntax:

```bash
pytest -m "integration and not slow"
```

---

### Flags for a debugging loop

Stop at the first failure:

```bash
pytest -x
```

Stop after three failures:

```bash
pytest --maxfail=3
```

Re-run only what failed last time:

```bash
pytest --lf
```

Run the previous failures first, then everything else:

```bash
pytest --ff
```

Drop into the debugger at the point of failure:

```bash
pytest --pdb
```

Show the slowest ten tests, which is how a slow suite gets diagnosed:

```bash
pytest --durations=10
```

Show print output and log records that pytest would otherwise capture:

```bash
pytest -s --log-cli-level=DEBUG
```

---

### Prove the suite is order-independent

Run each test the given number of times to expose a flake:

```bash
pytest --count=10
```

Shuffle the order, which surfaces every hidden dependency between tests:

```bash
pytest -p randomly
```

Both need a plugin, `pytest-repeat` and `pytest-randomly`. Treat an order-dependent failure as a defect in the test.

---

### Coverage reports

Terminal report naming the uncovered lines:

```bash
pytest --cov=mypackage --cov-report=term-missing
```

Browsable HTML report:

```bash
pytest --cov=mypackage --cov-report=html
```

Machine-readable report for a CI upload:

```bash
pytest --cov=mypackage --cov-report=xml
```

---

### Wire the gate into CI

The CI job runs the same command a developer runs, so a green local run means a green pipeline.

```yaml
- name: Test
  run: uv run pytest --cov=mypackage --cov-report=term-missing
```

The threshold comes from `[tool.coverage.report] fail_under`, so it is stated once and cannot drift between the local
run and the pipeline.
