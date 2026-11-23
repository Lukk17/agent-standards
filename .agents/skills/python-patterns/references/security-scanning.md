# Security scanning

pip-audit for the dependency set and bandit for first-party code. Open this when adding a security check to a project or to CI.

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
