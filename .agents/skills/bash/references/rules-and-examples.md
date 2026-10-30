# Bash rules with examples

Open this for the Pass and Fail form of any rule in [SKILL.md](../SKILL.md), and the reasoning behind it.

---

### Contents

- [Strict mode on every script](#strict-mode-on-every-script)
- [Quote every expansion](#quote-every-expansion)
- [Script structure template](#script-structure-template)
- [Doc Comments](#doc-comments)
- [Argument parsing](#argument-parsing)
- [Exit codes](#exit-codes)
- [Temporary files](#temporary-files)
- [Secret handling](#secret-handling)
- [Portability and ShellCheck](#portability-and-shellcheck)
- [Startup readiness log](#startup-readiness-log)

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
- Trap `EXIT` to run cleanup, so temp files and locks are removed even when the script crashes. Under `set -e` the
  `EXIT` trap also fires on an error, so an `ERR` trap for the same cleanup would run it twice.

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
- Validate arguments at entry, and call `usage 2 >&2` when one is missing or invalid, which prints usage to stderr
  and exits 2.
- Use `[[ ]]` rather than `[ ]`. It does not word-split its operands and it supports regex matching.

---

### Script structure template

Every non-trivial script follows one shape: header block, strict mode, constants, logging helpers, cleanup trap,
argument parsing, `main`, then a single `main "$@"` call. The full copyable template and the reasoning behind each
piece live in [references/script-template.md](script-template.md).

The header comment block carries the script name, a one-sentence description, the usage line, every option, every
exit code, and the minimum Bash version. `usage` prints the lines between the header's two dashed rules back, so the
two can never drift.

Pass:

```bash
usage() { sed -n '3,/^# --*$/{/^# --*$/d;s/^# //;p;}' "$0"; exit "${1:-0}"; }
```

Fail:

```bash
usage() { echo "usage: script.sh [-v] <path>"; exit 0; }
```

---

### Doc Comments

Function comments follow "Doc Comments" in `coding-standards`. The shell delta: a function has no signature, no types
and no named parameters, so the notes that earn a line are an argument's units, range or emptiness, what the function
prints to stdout (or that it prints nothing and sets a global), and every non-zero exit status a caller can act on,
which is always contract because nothing in shell declares it.

```bash
# Rotates the vault backups and prints the paths it removed.
# $2 is an age in days, values above 3650 are rejected.
# Exits 3 when the vault directory is missing.
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
caller decide. The two exceptions are `usage`, which ends the run with the code it is given (0 after `--help`, 2 on
misuse), and the `EXIT` trap handler, which re-raises the status it captured.

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
the `observability-and-logging` skill, in its `references/startup-readiness-log.md`.

Probe each dependency with a bounded timeout and surface only the status marker. Capture the exit code and send the
probe's own stderr to a debug log.

Pass:

```bash
probe() { if curl --silent --output /dev/null --max-time 2 --connect-timeout 2 "$1"; then echo "$1 [Connected]"; else echo "$1 [FAILED]"; fi; }
```

Fail:

```bash
curl "$dependency_url"
```
