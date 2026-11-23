# ShellCheck

The lint gate for every script. Open this when wiring ShellCheck into CI, clearing its findings, or suppressing one. The rule it serves is in [SKILL.md](../SKILL.md).

---

### Run it in CI with zero warnings

Run ShellCheck on every script in CI with a zero-warning policy, at `--severity=style`, and never mask its exit status with `|| true`. Suppress a rule only with an inline
`# shellcheck disable=SCxxxx` comment that states the justification.

Pass:

```bash
shellcheck --severity=style --external-sources scripts/*.sh
```

Fail:

```bash
shellcheck --severity=error scripts/deploy.sh || true
```

- Ref: https://www.shellcheck.net/
