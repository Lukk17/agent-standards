#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: setup-project.sh
# Description: Builds a throwaway consumer project inside the container and
#              imports the shared configuration from the mounted agent-standards
#              repository exactly as docs/AGENT_TOOLING.md tells a consumer to.
# Usage: setup-project.sh
# Environment:
#   AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
#   SANDBOX_PROJECT       Throwaway project directory. Default /work/project.
# Exit codes:
#   0  The project was created and every imported path landed.
#   1  A prerequisite was missing, the import failed, or a symlink did not
#      resolve.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly REPO="${AGENT_STANDARDS_REPO:-/repo}"
readonly PROJECT="${SANDBOX_PROJECT:-/work/project}"
readonly REMOTE="agent-standards"

readonly IMPORT_PATHS=(
  ".agents"
  ".claude"
  ".opencode"
  ".kilo"
  ".codex"
  ".github/agents"
  ".github/hooks"
  ".vscode/mcp.json"
  ".mcp.json"
  "opencode.json"
  "docs/AGENT_TOOLING.md"
  "docs/MCP_SETUP.md"
  "docs/AGENTS-UPDATE.md"
  "AGENTS.md.example"
)

readonly SYMLINKS=(
  ".claude/skills:../.agents/skills"
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

main() {
  require_tools
  require_source_repo
  create_empty_project
  import_standards
  verify_symlinks

  log_info "project ready at ${PROJECT}"
}

main "$@"
