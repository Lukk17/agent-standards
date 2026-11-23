# Scope

Companion reference for the [bash](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a `.sh` or `.bash` script.
- Adding argument parsing, a usage block, or exit codes to an existing script.
- Fixing a script that silently continues after a failed command.
- Hardening a script against word splitting, globbing, or an unset variable.
- Wiring ShellCheck into CI, or clearing its findings.
- Writing a shell wrapper that starts a long-running service.
- The user says "write a bash script for this", "why does my script keep going after an error", "this loop breaks on filenames with spaces" or "make ShellCheck pass".

---

### When not to activate

- Scripting on Windows or writing cmdlets and modules, use `powershell`.
- Writing the CI workflow YAML the script runs inside, use `deployment-patterns`.
- Writing the Dockerfile or entrypoint the script ships in, use `docker-patterns`.
- Driving infrastructure configuration that a playbook should own, use `ansible`.
- Writing Python instead because the script outgrew the shell, use `python-patterns`.

---

### Related skills

- `powershell` for the same standards on Windows.
- `observability-and-logging` for the readiness banner and the logging conventions it follows.
- `docker-patterns` for entrypoint scripts and container health checks.
- `deployment-patterns` for the CI workflow that runs ShellCheck and the script itself.
- `ansible` when the script is really configuration management in disguise.
