#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: mcp-guard.sh
# Description: Stands in for docker, npx and uvx, the only launchers the MCP
#              blocks this repository ships use, so no agent CLI in the
#              sandbox can start a real MCP server, pull an image or download
#              a package. Each call is recorded and refused.
# Usage: invoked through a link named docker, npx or uvx
# Environment:
#   SANDBOX_MCP_GUARD_LOG  File each refused call is appended to. Default
#                          /tmp/sandbox-mcp-guard.log.
# Exit codes:
#   127  Always, the way a missing launcher answers.
# -----------------------------------------------------------------------------
set -uo pipefail
IFS=$'\n\t'

readonly GUARD_LOG="${SANDBOX_MCP_GUARD_LOG:-/tmp/sandbox-mcp-guard.log}"

printf '%s %s\n' "$(basename "$0")" "$*" >>"$GUARD_LOG" 2>/dev/null

echo "mcp-guard: $(basename "$0") is blocked inside the sandbox" >&2

exit 127
