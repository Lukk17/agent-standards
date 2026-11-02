---
name: bash
description: Bash scripting standards for strict mode, quoting, argument parsing, exit codes, temp files, secret handling and ShellCheck. Use when the user says "write a bash script for this", "why does my script keep going after an error", "this loop breaks on filenames with spaces" or "make ShellCheck pass". Not for PowerShell scripting on Windows, use `powershell`.
---

# Bash Standards

How a shell script behaves when something goes wrong: it stops, it cleans up, and it says why. Every rule here exists because the default shell behaviour is to carry on after a failure and produce a half-finished result.

Written for Bash 5 and ShellCheck. Target Bash 4.4 or newer for anything that must run on older distributions, and say so in the script header.

| Task | Open |
|---|---|
| The Pass and Fail example and the reasoning behind any rule below | [references/rules-and-examples.md](references/rules-and-examples.md) |
| Starting a new script, or checking that one has the header, trap, and logging pieces | [references/script-template.md](references/script-template.md) |
| The readiness banner a shell-run service prints when it comes up | `references/startup-readiness-log.md` in the `observability-and-logging` skill |

---

### When to activate

- Writing or reviewing a `.sh` or `.bash` script.
- Adding argument parsing, a usage block, or exit codes to an existing script.
- Fixing a script that silently continues after a failed command.
- Hardening a script against word splitting, globbing, or an unset variable.
- Wiring ShellCheck into CI, or clearing its findings.
- Writing a shell wrapper that starts a long-running service.

---

### When not to activate

- Scripting on Windows or writing cmdlets and modules, use `powershell`.
- Writing the CI workflow YAML the script runs inside, use `deployment-patterns`.
- Writing the Dockerfile or entrypoint the script ships in, use `docker-patterns`.
- Driving infrastructure configuration that a playbook should own, use `ansible`.
- Writing Python instead because the script outgrew the shell, use `python-patterns`.

---

### Rules

1. Strict mode on every script: `set -euo pipefail` and `IFS=$'\n\t'` immediately after the shebang, never a bare `set -e`. Disable `nounset` with `set +u` only around an optional positional check, then re-enable it with `set -u`.
2. Trap `EXIT` to run cleanup, so temp files and locks go even on a crash. Under `set -e` the `EXIT` trap also fires on an error, so an `ERR` trap for the same cleanup would run it twice.
3. Quote every expansion, `rm -f -- "$target_file"`, because an unquoted one is split on whitespace and glob-expanded. Use `[[ ]]` rather than `[ ]`: it does not word-split and it supports regex matching.
4. Check required external commands with `command -v` before any logic runs. Validate arguments at entry and call `usage 2 >&2` on a missing or invalid one, which prints usage to stderr and exits 2.
5. One structure: header block, strict mode, constants, logging helpers, cleanup trap, argument parsing, `main`, then a single `main "$@"` call. The header carries the script name, a one-sentence description, the usage line, every option, every exit code and the minimum Bash version.
6. `usage` prints the header lines between its two dashed rules back with `sed`, never a hand-written `echo`, so the two cannot drift.
7. Parse single-character flags with `getopts` and long options with a manual `case` loop. Always implement `-h` and `--help`, printing usage and exiting 0.
8. Exit 0 for success, 1 for a general error, 2 for misuse such as a bad argument or a missing dependency, and 3 to 125 per script, documented in the header.
9. Never `exit` from inside a function: return a code and let the caller decide. The exceptions are `usage`, which ends the run with the code it is given, and the `EXIT` trap handler, which re-raises the status it captured.
10. Create every temp path with `mktemp` and remove it in the cleanup trap. A hardcoded `/tmp` path is a collision and a symlink attack.
11. Read a secret from a file or an environment variable scoped to the subprocess. Never take one as a positional argument, which every user on the host sees in `ps`, and never echo or log one.
12. Run ShellCheck on every script in CI at `--severity=style` with zero warnings, never masked by `|| true`. Suppress a rule only with an inline `# shellcheck disable=SCxxxx` that states the justification.
13. Document the minimum Bash version in the header, and flag Bash-only features (arrays, `[[ ]]`, `declare`) when the script might be sourced from a POSIX `sh`.
14. A shell-run long-running service (log aggregator, polling daemon, init wrapper) `cat`s the readiness banner from `observability-and-logging` immediately before `exec` or the main loop. Probe each dependency with a bounded timeout, print only the status marker, capture the exit code, and send the probe's stderr to a debug log.

---

### Doc Comments

Function comments follow "Doc Comments" in `coding-standards`. The shell delta: a function has no signature, no types and no named parameters, so the notes that earn a line are an argument's units, range or emptiness, what the function prints to stdout (or that it prints nothing and sets a global), and every non-zero exit status a caller can act on, which is always contract because nothing in shell declares it.

---

### Related skills

- `powershell` for the same standards on Windows.
- `observability-and-logging` for the readiness banner and the logging conventions it follows.
- `docker-patterns` for entrypoint scripts and container health checks.
- `deployment-patterns` for the CI workflow that runs ShellCheck and the script itself.
- `ansible` when the script is really configuration management in disguise.

---

### Checklist

- [ ] `set -euo pipefail` and `IFS=$'\n\t'` immediately after the shebang.
- [ ] Every variable expansion quoted, every test using `[[ ]]`.
- [ ] Required commands checked with `command -v` before any logic.
- [ ] Arguments validated at entry, `-h` and `--help` implemented, usage matches the header block.
- [ ] `trap cleanup EXIT` removes every temp file and lock.
- [ ] Temp paths created with `mktemp`, never hardcoded.
- [ ] No secret in a positional argument, an echo, or a log line.
- [ ] Exit codes documented in the header, functions return rather than exit, except `usage` and the `EXIT` trap.
- [ ] ShellCheck passes with zero findings, every suppression justified inline.
