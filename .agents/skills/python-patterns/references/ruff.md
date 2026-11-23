# ruff

ruff for lint and format. Open this when setting the linter up or when a lint or format check is missing in CI.

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

### Configure it in pyproject.toml

```toml
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "S", "B", "A"]
```

The `S` rule set covers much of what bandit reports, as [security-scanning.md](security-scanning.md) says.
