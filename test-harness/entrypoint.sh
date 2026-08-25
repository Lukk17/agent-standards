#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: entrypoint.sh
# Description: Updates every agent CLI to its newest published release, records
#              the resolved versions, then runs the container command.
# Usage: entrypoint.sh [COMMAND [ARGS...]]
# Environment:
#   HARNESS_SKIP_UPDATE  Set to 1 to keep the versions baked into the image.
# Exit codes:
#   0    The container command succeeded.
#   >0   Whatever the container command returned.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly PACKAGES=(
  "@anthropic-ai/claude-code"
  "@openai/codex"
  "opencode-ai"
  "@kilocode/cli"
  "@github/copilot"
)

readonly BINARIES=(
  "claude"
  "codex"
  "opencode"
  "kilocode"
  "copilot"
)

readonly VERSION_TIMEOUT=90

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_warn()  { echo "[WARN]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# Version npm currently has installed for a package, or "not-installed".
installed_version() {
  local package="$1"
  local manifest="${NPM_CONFIG_PREFIX}/lib/node_modules/${package}/package.json"

  if [[ -f "$manifest" ]]; then
    jq -r '.version // "unknown"' "$manifest"
  else
    echo "not-installed"
  fi
}

# Version the binary reports itself, or "unavailable" when it cannot be asked.
self_reported_version() {
  local binary="$1"
  local output=""

  if ! command -v "$binary" >/dev/null 2>&1; then
    echo "unavailable"
    return 0
  fi

  if ! output="$(timeout "$VERSION_TIMEOUT" "$binary" --version </dev/null 2>/dev/null)"; then
    echo "unavailable"
    return 0
  fi

  echo "${output//$'\n'/ }" | tr -s ' ' | sed 's/^ *//;s/ *$//'
}

update_agents() {
  if [[ "${HARNESS_SKIP_UPDATE:-0}" == "1" ]]; then
    log_warn "HARNESS_SKIP_UPDATE=1, keeping the versions baked into the image"
    return 0
  fi

  local package
  for package in "${PACKAGES[@]}"; do
    log_info "updating ${package} to latest"

    if ! npm install --global --loglevel=error "${package}@latest"; then
      log_warn "could not update ${package}, continuing with the image version"
    fi
  done
}

report_versions() {
  local index

  echo "=============================================================="
  echo " Agent CLI versions under test"
  echo "=============================================================="
  printf '%-28s %-14s %s\n' "PACKAGE" "NPM VERSION" "SELF REPORTED"

  for index in "${!PACKAGES[@]}"; do
    printf '%-28s %-14s %s\n' \
      "${PACKAGES[$index]}" \
      "$(installed_version "${PACKAGES[$index]}")" \
      "$(self_reported_version "${BINARIES[$index]}")"
  done

  printf '%-28s %-14s %s\n' "node" "$(node --version)" "-"
  printf '%-28s %-14s %s\n' "python3" "$(python3 --version | awk '{print $2}')" "-"
  printf '%-28s %-14s %s\n' "git" "$(git --version | awk '{print $3}')" "-"
  echo "=============================================================="
}

main() {
  update_agents
  report_versions

  if [[ $# -eq 0 ]]; then
    exec /bin/bash
  fi

  exec "$@"
}

main "$@"
