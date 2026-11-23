#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: setup-project.sh
# Description: Builds a throwaway consumer project inside the container and
#              imports the shared configuration from the mounted agent-standards
#              repository as docs/AGENT_TOOLING.md tells a consumer to: the
#              Git checkout for OpenCode, Kilo Code, Codex and Copilot, and
#              for Claude Code the marketplace added and its plugins installed
#              at project scope (lib-claude-plugins.sh). A machine with no
#              claude command skips the Claude Code step, as a project that
#              never runs Claude Code does.
# Usage: setup-project.sh
# Environment:
#   AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
#   SANDBOX_PROJECT       Throwaway project directory. Default /work/project.
# Exit codes:
#   0  The project was created and every imported path landed.
#   1  A prerequisite was missing, the import failed, a symlink did not
#      resolve, or the Claude Code plugins could not be installed.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly REPO="${AGENT_STANDARDS_REPO:-/repo}"
readonly PROJECT="${SANDBOX_PROJECT:-/work/project}"
readonly REMOTE="agent-standards"

# shellcheck source=lib-claude-plugins.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib-claude-plugins.sh"

readonly IMPORT_PATHS=(
  ".agents"
  ".claude/workflows"
  ".opencode"
  ".kilo"
  ".codex"
  ".github/agents"
  ".github/hooks"
  ".github/mcp.json"
  ".vscode/mcp.json"
  ".mcp.json"
  "opencode.json"
  "docs/AGENT_TOOLING.md"
  "docs/MCP_SETUP.md"
  "docs/AGENTS-UPDATE.md"
  "AGENTS.md.example"
  ".metrics/tools"
)

readonly SYMLINKS=(
  ".opencode/agents:../.agents/agents"
  ".kilo/agents:../.agents/agents"
)

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

require_tools() {
  local tool
  for tool in git python3 jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      log_error "required command not found: ${tool}"
      exit 1
    fi
  done
}

require_source_repo() {
  if [[ ! -d "${REPO}/.git" ]]; then
    log_error "no git repository at ${REPO}; mount the agent-standards checkout there"
    exit 1
  fi
}

create_empty_project() {
  log_info "creating a clean project at ${PROJECT}"

  rm -rf "$PROJECT"
  mkdir -p "$PROJECT"
  cd "$PROJECT"

  git init --initial-branch=main --quiet
  git config user.name "agent-standards sandbox"
  git config user.email "sandbox@example.invalid"
}

# Echoes the fully qualified upstream ref the import should read.
upstream_ref() {
  local branch
  for branch in master main; do
    if git rev-parse --verify --quiet "${REMOTE}/${branch}" >/dev/null; then
      echo "${REMOTE}/${branch}"
      return 0
    fi
  done

  log_error "neither ${REMOTE}/master nor ${REMOTE}/main exists after fetch"
  return 1
}

import_standards() {
  local ref

  git config --global --add safe.directory "$REPO"
  git config --global --add safe.directory "${REPO}/.git"
  git config --global --add safe.directory "$PROJECT"

  log_info "adding the read-only ${REMOTE} remote pointing at ${REPO}"
  git remote add "$REMOTE" "$REPO"
  git remote set-url --push "$REMOTE" no_push

  log_info "fetching ${REMOTE}"
  git fetch --quiet "$REMOTE"

  ref="$(upstream_ref)"
  log_info "importing from ${ref}"
  git checkout "$ref" -- "${IMPORT_PATHS[@]}"

  log_info "activating the one template"
  mv AGENTS.md.example AGENTS.md
}

repair_symlink() {
  local link="$1"
  local target="$2"

  if [[ -L "$link" ]]; then
    return 0
  fi

  log_info "recreating ${link} as a symlink, the checkout did not deliver one"
  rm -rf "$link"
  mkdir -p "$(dirname "$link")"
  ln -s "$target" "$link"
}

verify_symlinks() {
  local entry link target failures=0

  for entry in "${SYMLINKS[@]}"; do
    link="${entry%%:*}"
    target="${entry##*:}"

    repair_symlink "$link" "$target"

    if [[ -L "$link" && -d "$link" ]]; then
      log_info "symlink resolves: ${link} -> $(readlink "$link")"
    else
      log_error "symlink does not resolve: ${link}"
      failures=$((failures + 1))
    fi
  done

  if [[ "$failures" -gt 0 ]]; then
    log_error "${failures} symlink(s) did not resolve"
    return 1
  fi
}

# Claude Code takes its skills, subagents and hooks from the marketplace, so
# the project gets no .claude/skills, no .claude/agents and no hook wiring by
# checkout: the install writes .claude/settings.json itself.
install_claude_plugins() {
  local IFS=' '

  if ! command -v claude >/dev/null 2>&1; then
    log_info "no claude command on PATH, skipping the Claude Code plugins"
    return 0
  fi

  log_info "adding the marketplace and installing ${CLAUDE_PROJECT_PLUGINS[*]} at project scope"

  if ! claude_market_start "$REPO"; then
    log_error "the marketplace could not be served from ${REPO} on port ${CLAUDE_MARKET_PORT}"
    return 1
  fi

  if ! claude_plugins_install "$PROJECT" >&2; then
    log_error "the Claude Code plugins could not be installed into ${PROJECT}"
    return 1
  fi
}

main() {
  trap claude_market_stop EXIT

  require_tools
  require_source_repo
  create_empty_project
  import_standards
  verify_symlinks
  install_claude_plugins

  log_info "project ready at ${PROJECT}"
}

main "$@"
