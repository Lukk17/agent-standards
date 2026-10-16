#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: opencode2.sh
# Description: Runs OpenCode 2.x, installed as @opencode/cli in its own npm
#              prefix, with its own data directory. Installed on PATH as
#              opencode2, because @opencode/cli and opencode-ai both own the
#              opencode binary name.
# Usage: opencode2 [ARGS...]
# Environment:
#   OPENCODE2_PREFIX     npm prefix holding @opencode/cli. Default
#                        ~/.opencode-v2.
#   OPENCODE2_DATA_HOME  XDG_DATA_HOME handed to 2.x. Default
#                        ~/.local/share/opencode-v2.
# Exit codes:
#   127  No 2.x binary under the prefix.
#   *    Whatever OpenCode 2.x returned.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# Both majors keep their database at $XDG_DATA_HOME/opencode/opencode.db, and
# 1.x refuses to start once 2.x has created it there ("Database is not empty
# and has no session table"). Moving only the data directory keeps both
# working while they still share the configuration directory, which is the
# part the suites assert on.
readonly V2_BIN="${OPENCODE2_PREFIX:-${HOME}/.opencode-v2}/bin/opencode"

if [[ ! -x "$V2_BIN" ]]; then
  echo "opencode2: no OpenCode 2.x binary at ${V2_BIN}" >&2
  exit 127
fi

export XDG_DATA_HOME="${OPENCODE2_DATA_HOME:-${HOME}/.local/share/opencode-v2}"

exec "$V2_BIN" "$@"
