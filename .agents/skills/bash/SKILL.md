---
name: bash
description: Bash scripting standards covering strict mode, defensive patterns, argument parsing, exit codes, and ShellCheck enforcement.
origin: project-standards
---

# Bash Standards

## Core Execution Directives

- Treat all LLM generated scripts, variable expansions, and command pipelines as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every script generation task.
- Append a Zero-Trust directive demanding mandatory web searches for current Bash built-ins.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every command flag and syntax structure provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

## Strict Mode and Error Handling

- Enforce the Unofficial Bash Strict Mode at the top of every script to prevent silent failures and unbound variable errors.
  - Ref: http://redsymbol.net/articles/unofficial-bash-strict-mode/
- Require the agent to prepend the following line immediately after the shebang:

```bash
set -euo pipefail
IFS=$'\n\t'
```

- Disable the `nounset` option temporarily using `set +u` only when checking for optional positional parameters, then immediately re-enable it using `set -u`.
- Use the `trap` built-in to catch `ERR` signals and execute cleanup functions, ensuring temporary files or locks are removed even if the script crashes unexpectedly.

---

## Defensive Scripting Practices

- Quote all variable expansions to prevent word splitting and globbing issues. Use `"$VARIABLE"` instead of `$VARIABLE`.
- Validate the presence of required external commands using `command -v` at the start of the script before executing any logic.
- Validate all required positional or named arguments at script entry; print a usage message and exit 1 if any are missing or invalid.
- Use `[[ ]]` for conditional tests instead of `[ ]`; the double-bracket form is safer and supports regex matching.

---

## Script Structure Template

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

## Argument Parsing

- Use `getopts` for single-character flags; use a manual `case` statement for long options (`--flag`).
- Always implement `-h` / `--help` that prints usage and exits 0.
- Document every flag and argument in the header comment block.

---

## Exit Code Conventions

- Exit `0` for success.
- Exit `1` for general errors (catch-all).
- Exit `2` for misuse of the script (wrong arguments, missing dependencies).
- Exit codes `3`–`125` may be defined per-script for specific error conditions; document them in the header.
- Never `exit` from inside a function; `return` a non-zero code and let the caller decide.

---

## Temporary Files

- Always create temp files with `mktemp`; never hardcode `/tmp/script-name.tmp`.
- Always remove temp files in the `cleanup` trap; never rely on manual cleanup at the end of the script.
- Use `mktemp -d` for temp directories; remove them with `rm -rf "$TMPDIR"` inside `cleanup`.

---

## Secret Handling

- Never echo, print, or log secrets. If a secret must be passed to a subprocess, use a file descriptor or environment variable scoped to that subprocess.
- Read secrets from files or environment variables; never accept them as positional command-line arguments (they appear in `ps` output).

---

## Portability and ShellCheck

- Explicitly target Bash 4.x or higher; document the minimum required version in the header comment.
- Flag Bash-only features (arrays, `[[ ]]`, `declare`) with a comment if the script might be sourced in a POSIX `sh` context.
- Run **ShellCheck** on every script in CI with zero warnings/errors policy. Suppress individual rules only with an inline `# shellcheck disable=SCxxxx` comment that includes a justification.
  - Ref: https://www.shellcheck.net/
