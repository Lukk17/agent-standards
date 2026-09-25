#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: opencode.sh
# Description: Runs OpenCode headless against Requesty (OpenAI Chat
#              Completions format) and asserts on its exported sessions. The
#              provider arrives through OPENCODE_CONFIG_CONTENT.
# Usage: opencode.sh [health|run|all] [-h|--help]
# Environment: REQUESTY_API_KEY plus the LIVE_* variables documented in lib.sh.
# Exit codes: as lib.sh.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly AGENT_LABEL="opencode"
readonly AGENT_BIN="opencode"
readonly AGENT_NPM_PACKAGE="opencode-ai"
readonly CONFIG_CONTENT_VAR="OPENCODE_CONFIG_CONTENT"

# shellcheck source=sandbox-agent/live/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=sandbox-agent/live/opencode-family.sh
source "$(dirname "${BASH_SOURCE[0]}")/opencode-family.sh"

live_main "$@"
