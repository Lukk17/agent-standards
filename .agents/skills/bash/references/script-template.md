# Bash script template

The shape every non-trivial script follows: header block, strict mode, constants, logging helpers, cleanup trap,
usage, `main`, then a single `main "$@"` call. Copy it and delete what the script does not need.

---

```bash
#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: script-name.sh
# Description: One-sentence description of what this script does.
# Usage: ./script-name.sh [OPTIONS] <required-arg>
# Requires: Bash 4.4 or newer
# Options:
#   -h, --help    Show this help message and exit
#   -v, --verbose Enable verbose output
# Exit codes:
#   0  success
#   1  general error
#   2  misuse (bad argument, missing dependency)
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
  exit "$exit_code"
}
trap cleanup EXIT

# --- Argument Parsing --------------------------------------------------------
usage() {
  grep '^#' "$0" | sed 's/^# \?//'
  exit 0
}

main() {
  :
}

main "$@"
```

---

### Why the pieces are there

The header comment block is the single source of truth for the usage text: `usage` prints the block back with the
comment markers stripped, so the documentation and the help output cannot drift apart.

`readonly SCRIPT_DIR` resolves the script's own directory even when the script is invoked through a symlink or from
another working directory, which is what makes sibling-file lookups reliable.

Logging helpers write to stderr so a caller can pipe the script's real output without the diagnostics mixing in.

`trap cleanup EXIT` runs on a normal exit, on an error under `set -e`, and on most signals, which is why temp file
removal and lock release belong there rather than at the bottom of `main`.

The `local exit_code=$?` capture on the first line of `cleanup` preserves the original status. Anything that runs
before that line overwrites `$?` and the script exits reporting success.
