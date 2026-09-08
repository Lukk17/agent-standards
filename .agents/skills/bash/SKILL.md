---
name: bash
description: Bash scripting standards covering strict mode, quoting and defensive patterns, argument parsing, exit codes, temp files, secret handling, and ShellCheck enforcement. Use when you say "write a bash script for this", "why does my script keep going after an error", "parse these flags properly", "this loop breaks on filenames with spaces", or "make ShellCheck pass". Not for PowerShell scripting on Windows, use `powershell`.
---

# Bash Standards

How a shell script behaves when something goes wrong: it stops, it cleans up, and it says why. Every rule here exists
because the default shell behaviour is to carry on after a failure and produce a half-finished result.

Baseline: Bash 5.3 (verified locally) and ShellCheck current stable. Target Bash 4.4 or newer for anything that must
run on older distributions, and say so in the script header.

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

### Strict mode on every script

Enable strict mode immediately after the shebang so an unset variable, a failed command, or a broken pipe stops the
script instead of poisoning the rest of the run.

Pass:

```bash
set -euo pipefail
```

Fail:

```bash
set -e
```

- Ref: http://redsymbol.net/articles/unofficial-bash-strict-mode/
- Set `IFS=$'\n\t'` alongside it so word splitting no longer happens on spaces.
- Disable `nounset` with `set +u` only around an optional positional check, then re-enable it with `set -u`.
- Trap `ERR` and `EXIT` to run cleanup, so temp files and locks are removed even when the script crashes.

---

### Quote every expansion

An unquoted expansion is split on whitespace and glob-expanded. That is the single most common shell defect.

Pass:

```bash
rm -f -- "$target_file"
```

Fail:

```bash
rm -f $target_file
```

- Validate required external commands with `command -v` before any logic runs.
- Validate arguments at entry, print usage, and exit 2 when one is missing or invalid.
- Use `[[ ]]` rather than `[ ]`. It does not word-split its operands and it supports regex matching.

---

### Script structure template

Every non-trivial script follows one shape: header block, strict mode, constants, logging helpers, cleanup trap,
argument parsing, `main`, then a single `main "$@"` call. The full copyable template and the reasoning behind each
piece live in [references/script-template.md](references/script-template.md).

The header comment block carries the script name, a one-sentence description, the usage line, every option, every
exit code, and the minimum Bash version. `usage` prints it back, so the two can never drift.

Pass:

```bash
usage() { grep '^#' "$0" | sed 's/^# \?//'; exit 0; }
```

Fail:

```bash
usage() { echo "usage: script.sh [-v] <path>"; exit 0; }
```

---

### Doc Comments

Default to none. A comment block above a function is usually a sign that the code failed to explain itself. Before
writing one, extract the unclear block into a well-named function, rename the arguments so they carry their own
meaning, and tighten the types. Do that first and most comment blocks have nothing left to say, which is the outcome
you want. Code that explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every note you add about an
argument, the output, or an exit status is capped at one line and only appears when it genuinely adds something: if
the note does not fit on a single line, shorten it or drop it. Four rules decide what goes in. Shell has no signature
at all, no types and no named parameters, so the little that is worth saying is worth saying precisely.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. Describe an argument only when the name at the call site does not already convey it, meaning units, a valid range,
   whether it may be empty, or who removes it afterwards. `$1 - the vault` is noise, delete it.
3. Describe what the function writes to stdout only when it is non-obvious, and say so explicitly when it writes
   nothing but sets a global.
4. Describe every non-zero exit status a caller can act on, always. Nothing in shell declares them, so this one is
   genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a note line has no exception at all: shorten it or
delete it.

Pass, one line, then only what the call site cannot show:

```bash
# Rotates the vault backups and prints the paths it removed.
# $2 is an age in days, values above 3650 are rejected.
# Exits 3 when the vault directory is missing.
rotate_backups() { :; }
```

Fail, restates the function name and numbers the arguments for no gain:

```bash
# This function rotates backups.
# $1 - the vault
# $2 - the days
rotate_backups() { :; }
```

---

### Argument parsing

Use `getopts` for single-character flags and a manual `case` loop for long options. Always implement `-h` and
`--help`, printing usage and exiting 0.

Pass:

```bash
while [[ $# -gt 0 ]]; do case "$1" in -h|--help) usage ;; -v|--verbose) verbose=1; shift ;; *) break ;; esac; done
```

Fail:

```bash
verbose="$1"
```

---

### Exit codes

Exit 0 for success, 1 for a general error, 2 for misuse such as a bad argument or a missing dependency. Codes 3 to
125 are per-script and documented in the header. Never `exit` from inside a function, return a code and let the
caller decide.

Pass:

```bash
validate_input() { [[ -n "${1:-}" ]] || return 2; }
```

Fail:

```bash
validate_input() { [[ -n "$1" ]] || exit 2; }
```

---

### Temporary files

Create every temp path with `mktemp` and remove it in the cleanup trap. A hardcoded path in `/tmp` is a collision and
a symlink attack waiting to happen.

Pass:

```bash
tmp_dir="$(mktemp -d)"
```

Fail:

```bash
tmp_dir="/tmp/my-script.tmp"
```

---

### Secret handling

Read secrets from a file or an environment variable scoped to the subprocess. Never accept one as a positional
argument, it is visible in `ps` output to every user on the host, and never echo or log one.

Pass:

```bash
API_TOKEN="$(< /run/secrets/api_token)" ./deploy.sh
```

Fail:

```bash
./deploy.sh --token "sk-live-1234567890"
```

---

### Portability and ShellCheck

Run ShellCheck on every script in CI with a zero-warning policy. Suppress a rule only with an inline
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
- Document the minimum Bash version in the header, and flag Bash-only features (arrays, `[[ ]]`, `declare`) when the
  script might be sourced from a POSIX `sh`.

---

### Startup readiness log

For a shell-implemented long-running service (a log aggregator, a polling daemon, an init wrapper around a child
process), `cat` the readiness banner immediately before `exec` or the main loop. The universal convention, the ANSI
Shadow banner, the section order, and the probe rules live in
[observability-and-logging/references/startup-readiness-log.md](../observability-and-logging/references/startup-readiness-log.md).

Probe each dependency with a bounded timeout and surface only the status marker. Capture the exit code and send the
probe's own stderr to a debug log.

Pass:

```bash
probe() { curl --silent --output /dev/null --max-time 2 --connect-timeout 2 "$1" && echo "$1 [Connected]" || echo "$1 [FAILED]"; }
```

Fail:

```bash
curl "$dependency_url"
```

---

### Reference files

| Open this | For |
|---|---|
| [references/script-template.md](references/script-template.md) | Starting a new script, or checking that an existing one has the header, trap, and logging pieces |
| [../observability-and-logging/references/startup-readiness-log.md](../observability-and-logging/references/startup-readiness-log.md) | Writing the readiness banner a shell-run service prints when it comes up |

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
- [ ] Exit codes documented in the header, functions return rather than exit.
- [ ] ShellCheck passes with zero findings, every suppression justified inline.
