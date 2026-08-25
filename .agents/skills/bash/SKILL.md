---
name: bash
description: Bash scripting standards covering strict mode, defensive patterns, argument parsing, exit codes, and ShellCheck enforcement.
origin: project-standards
---

# Bash Standards

---

### Core Execution Directives

- Treat all LLM generated scripts, variable expansions, and command pipelines as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every script generation task.
- Append a Zero-Trust directive demanding mandatory web searches for current Bash built-ins.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation
  cannot be retrieved via live search.
- Require exact confidence percentage scores for every command flag and syntax structure provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Strict Mode and Error Handling

- Enforce the Unofficial Bash Strict Mode at the top of every script to prevent silent failures and unbound variable
  errors.
  - Ref: http://redsymbol.net/articles/unofficial-bash-strict-mode/
- Require the agent to prepend the following line immediately after the shebang:

```bash
set -euo pipefail
IFS=$'\n\t'
```

- Disable the `nounset` option temporarily using `set +u` only when checking for optional positional parameters, then
  immediately re-enable it using `set -u`.
- Use the `trap` built-in to catch `ERR` signals and execute cleanup functions, ensuring temporary files or locks are
  removed even if the script crashes unexpectedly.

---

### Defensive Scripting Practices

- Quote all variable expansions to prevent word splitting and globbing issues. Use `"$VARIABLE"` instead of `$VARIABLE`.
- Validate the presence of required external commands using `command -v` at the start of the script before executing any
  logic.
- Validate all required positional or named arguments at script entry; print a usage message and exit 1 if any are
  missing or invalid.
- Use `[[ ]]` for conditional tests instead of `[ ]`; the double-bracket form is safer and supports regex matching.

---

### Script Structure Template

Every non-trivial script must follow this structure:

```bash
#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: script-name.sh
# Description: One-sentence description of what this script does.
# Usage: ./script-name.sh [OPTIONS] <required-arg>
# Options:
#   -h, --help    Show this help message and exit
#   -v, --verbose Enable verbose output
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# --- Constants ---------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "$0")"

# --- Logging -----------------------------------------------------------------
log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_warn()  { echo "[WARN]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# --- Cleanup -----------------------------------------------------------------
cleanup() {
  local exit_code=$?
  # Remove temp files, release locks, etc.
  exit "$exit_code"
}
trap cleanup EXIT

# --- Argument Parsing --------------------------------------------------------
usage() {
  grep '^#' "$0" | sed 's/^# \?//'
  exit 0
}

main() {
  # Script logic here
  :
}

main "$@"
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

```bash
# Good: one line, then only what the call site cannot show
# Rotates the vault backups and prints the paths it removed.
# $2 is an age in days, values above 3650 are rejected.
# Exits 3 when the vault directory is missing.
rotate_backups() { :; }

# Bad: restates the function name and numbers the arguments for no gain
# This function rotates backups.
# $1 - the vault
# $2 - the days
rotate_backups() { :; }
```

---

### Argument Parsing

- Use `getopts` for single-character flags; use a manual `case` statement for long options (`--flag`).
- Always implement `-h` / `--help` that prints usage and exits 0.
- Document every flag and argument in the header comment block.

---

### Exit Code Conventions

- Exit `0` for success.
- Exit `1` for general errors (catch-all).
- Exit `2` for misuse of the script (wrong arguments, missing dependencies).
- Exit codes `3`-`125` may be defined per-script for specific error conditions; document them in the header.
- Never `exit` from inside a function; `return` a non-zero code and let the caller decide.

---

### Temporary Files

- Always create temp files with `mktemp`; never hardcode `/tmp/script-name.tmp`.
- Always remove temp files in the `cleanup` trap; never rely on manual cleanup at the end of the script.
- Use `mktemp -d` for temp directories; remove them with `rm -rf "$TMPDIR"` inside `cleanup`.

---

### Secret Handling

- Never echo, print, or log secrets. If a secret must be passed to a subprocess, use a file descriptor or environment
  variable scoped to that subprocess.
- Read secrets from files or environment variables; never accept them as positional command-line arguments (they appear
  in `ps` output).

---

### Portability and ShellCheck

- Explicitly target Bash 4.x or higher; document the minimum required version in the header comment.
- Flag Bash-only features (arrays, `[[ ]]`, `declare`) with a comment if the script might be sourced in a POSIX `sh`
  context.
- Run ShellCheck on every script in CI with zero warnings/errors policy. Suppress individual rules only with an inline
  `# shellcheck disable=SCxxxx` comment that includes a justification.
  - Ref: https://www.shellcheck.net/

---

### Startup readiness log

See [observability-and-logging](../observability-and-logging/SKILL.md) → "Startup readiness log" for the universal
convention (ANSI Shadow
banner, URL + profile + dependency + observability sections, 2-second probe timeouts, `<url> [Connected|Warning|FAILED]`
result format).

For shell-implemented long-running services (log aggregators, polling daemons, init wrappers around a child process),
`cat` the banner immediately before `exec` or the main loop:

```bash
cat <<'EOF'
███████╗██╗   ██╗██████╗ ██████╗ ██╗     ██╗███████╗██████╗
██╔════╝██║   ██║██╔══██╗██╔══██╗██║     ██║██╔════╝██╔══██╗
███████╗██║   ██║██████╔╝██████╔╝██║     ██║█████╗  ██████╔╝
╚════██║██║   ██║██╔═══╝ ██╔═══╝ ██║     ██║██╔══╝  ██╔══██╗
███████║╚██████╔╝██║     ██║     ███████╗██║███████╗██║  ██║
╚══════╝ ╚═════╝ ╚═╝     ╚═╝     ╚══════╝╚═╝╚══════╝╚═╝  ╚═╝
EOF
```

Then the readiness lines (profile, hostname, dependencies, observability), then the `exec`:

```bash
exec /usr/local/bin/my-daemon
```

Probe timeouts: `curl --max-time 2 --connect-timeout 2 <url>` for each dependency check. Capture the exit code, redirect
probe stderr to a debug log file, surface only `[Connected]` / `[FAILED]` in the banner:

```bash
probe() {
  local url="$1"
  if curl --silent --output /dev/null --max-time 2 --connect-timeout 2 "$url"; then
    printf '%s [Connected]\n' "$url"
  else
    printf '%s [FAILED]\n' "$url"
  fi
}
```
