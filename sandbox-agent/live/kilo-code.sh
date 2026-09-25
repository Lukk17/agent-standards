#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: kilo-code.sh
# Description: Runs Kilo Code headless against Requesty (OpenAI Chat
#              Completions format) and asserts on its exported sessions. The
#              provider arrives through KILO_CONFIG_CONTENT, one of the trusted
#              config sources where Kilo resolves an {env:} reference.
# Usage: kilo-code.sh [health|run|all] [-h|--help]
# Environment: REQUESTY_API_KEY plus the LIVE_* variables documented in lib.sh.
# Exit codes: as lib.sh.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly AGENT_LABEL="kilo-code"
readonly AGENT_BIN="kilo"
readonly AGENT_NPM_PACKAGE="@kilocode/cli"
readonly CONFIG_CONTENT_VAR="KILO_CONFIG_CONTENT"

# shellcheck source=sandbox-agent/live/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=sandbox-agent/live/opencode-family.sh
source "$(dirname "${BASH_SOURCE[0]}")/opencode-family.sh"

live_main "$@"
