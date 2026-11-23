---
name: bash
description: 'Bash script standards: strict mode, quoting, argument parsing, exit codes, temp files and secrets. Use when the user says "write a bash script" or "make ShellCheck pass". Not for Windows, use `powershell`.'
metadata:
  version: "1.1.0"
---

# Bash Standards

How a shell script behaves when something goes wrong: it stops, it cleans up, and it says why. Every rule here exists because the default shell behaviour is to carry on after a failure and produce a half-finished result.

Written for Bash 5 and ShellCheck. Target Bash 4.4 or newer for anything that must run on older distributions, and say so in the script header.

---

### When not to activate

- Scripting on Windows or writing cmdlets and modules, use `powershell`.
- Writing the Dockerfile or entrypoint the script ships in, use `docker-patterns`.
- Writing Python instead because the script outgrew the shell, use `python-patterns`.

---

### Rules

1. Strict mode on every script: `set -euo pipefail` and `IFS=$'\n\t'` immediately after the shebang, never a bare `set -e`.
2. Trap `EXIT` to run cleanup, so temp files and locks go even on a crash, and add no `ERR` trap for the same cleanup.
3. Quote every expansion, and test with `[[ ]]` rather than `[ ]`.
4. Check required external commands with `command -v` and validate arguments before any logic runs. A missing or invalid argument prints usage to stderr and exits 2.
5. One structure: header block, strict mode, constants, logging helpers, cleanup trap, argument parsing, `main`, then a single `main "$@"` call. `usage` prints the header back, so the two cannot drift.
6. Parse single-character flags with `getopts` and long options with a manual `case` loop. Always implement `-h` and `--help`, printing usage and exiting 0.
7. Exit 0 for success, 1 for a general error, 2 for misuse, and 3 to 125 per script, documented in the header. A function returns a code and never calls `exit`, except `usage` and the `EXIT` trap handler.
8. Create every temp path with `mktemp` and remove it in the cleanup trap, never a hardcoded `/tmp` path.
9. Read a secret from a file or an environment variable scoped to the subprocess. Never take one as a positional argument, and never echo or log one.
10. Lint every script in CI with zero warnings, never masked, and suppress a finding only inline with its justification.
11. Document the minimum Bash version in the header, and flag Bash-only features when the script might be sourced from a POSIX `sh`.
12. A long-running service started from a shell prints its readiness banner immediately before `exec` or the main loop, with each dependency probed under a bounded timeout.
13. Function comments follow "Doc Comments" in `coding-standards`. A line is earned only by an argument's units, range or emptiness, by what the function prints to stdout, and by each non-zero exit status a caller can act on.

---

### Reference files

| Open this | When |
| --- | --- |
| [rules-and-examples.md](references/rules-and-examples.md) | A rule above needs its Pass and Fail example or its reasoning. |
| [script-template.md](references/script-template.md) | Starting a new script, or checking that one has the header, trap and logging pieces. |
| [shellcheck.md](references/shellcheck.md) | Wiring ShellCheck into CI, clearing its findings, or suppressing one. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a script done. |
