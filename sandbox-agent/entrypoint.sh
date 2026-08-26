#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: entrypoint.sh
# Description: Refuses the run when the scripts baked into the image no longer
#              match the ones on the mounted repository, marks the mounted
#              repository as a git safe directory, updates every agent CLI to
#              its newest published release, records the resolved versions,
#              then runs the container command.
# Usage: entrypoint.sh [COMMAND [ARGS...]]
# Environment:
#   AGENT_STANDARDS_REPO     Mounted upstream repository. Default /repo.
#   SANDBOX_SKIP_UPDATE      Set to 1 to keep the versions baked into the image.
#   SANDBOX_SKIP_STALE_CHECK Set to 1 to run the baked scripts even when they no
#                            longer match the mounted repository.
# Exit codes:
#   0    The container command succeeded.
#   2    The git safe.directory entries could not be written.
#   3    The scripts baked into the image no longer match the mounted repository.
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

readonly REPO="${AGENT_STANDARDS_REPO:-/repo}"

# The scripts are copied into the image at build time and the repository is
# mounted at run time, so the two drift apart the moment anyone edits a script
# without rebuilding. docker compose run does not rebuild, so a run would
# silently assert the old script and report a result about code that no longer
# exists. These two directories are the two copies to compare.
readonly IMAGE_SCRIPTS="/sandbox"
readonly REPO_SCRIPTS="${REPO}/sandbox-agent"

# Both entries are needed. Git checks the working tree it discovered and the
# repository directory it resolved, and a clone whose source is a path is keyed
# on that path's .git directory, so trusting only the working tree is not enough.
readonly SAFE_DIRECTORIES=(
  "$REPO"
  "${REPO}/.git"
)

log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_warn()  { echo "[WARN]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# True when git already trusts the given directory for this container user.
already_trusted() {
  local directory="$1"

  git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$directory"
}

# Lets git read the bind-mounted repository, which a Docker Desktop host on
# Windows presents as owned by root while the container runs as sandbox.
trust_mounted_repo() {
  local directory

  for directory in "${SAFE_DIRECTORIES[@]}"; do
    if already_trusted "$directory"; then
      log_info "git already trusts ${directory}"
      continue
    fi

    if ! git config --global --add safe.directory "$directory"; then
      log_error "could not mark ${directory} as a git safe directory"
      return 1
    fi

    log_info "marked ${directory} as a git safe directory"
  done
}

# Every *.sh basename present in either copy, listed once, sorted. Derived from
# the directories rather than from a list, so a script added to the Dockerfile's
# COPY is covered without editing anything here, and a script that exists only
# on one side still counts as a difference.
script_names() {
  local directory path

  for directory in "$IMAGE_SCRIPTS" "$REPO_SCRIPTS"; do
    for path in "$directory"/*.sh; do
      [[ -f "$path" ]] || continue

      basename "$path"
    done
  done | sort -u
}

# Content digest of a file, "absent" when there is nothing at that path, and an
# empty string when something is there but cannot be hashed. The caller treats
# those three answers differently: absent is a real difference, unhashable is
# not something to judge on.
file_digest() {
  local path="$1"

  if [[ ! -e "$path" ]]; then
    echo "absent"
    return 0
  fi

  sha256sum "$path" 2>/dev/null | cut -d' ' -f1
}

report_stale() {
  local name

  echo "==============================================================" >&2
  echo " STALE IMAGE, refusing to run" >&2
  echo "==============================================================" >&2
  log_error "these scripts differ from the ones in ${REPO_SCRIPTS}:"

  for name in "$@"; do
    echo "         - ${name}" >&2
  done

  log_error "the image was built before those edits and 'docker compose run' does not rebuild,"
  log_error "so this run would assert against code that no longer exists. Rebuild first:"
  echo >&2
  echo "         docker compose run --rm --build sandbox" >&2
  echo >&2
  log_error "to run the baked scripts anyway, set SANDBOX_SKIP_STALE_CHECK=1"
  echo "==============================================================" >&2
}

# Refuses the run when the baked scripts no longer match the mounted ones. Only
# ever fires on positive evidence: both copies readable and their bytes differ,
# or one copy missing entirely. Anything that makes the comparison impossible
# skips the check instead, so the guard cannot become a new way to break a run.
assert_scripts_are_fresh() {
  if [[ "${SANDBOX_SKIP_STALE_CHECK:-0}" == "1" ]]; then
    log_warn "SANDBOX_SKIP_STALE_CHECK=1, running the baked scripts without comparing them"
    return 0
  fi

  if [[ ! -d "$REPO_SCRIPTS" ]]; then
    log_info "no ${REPO_SCRIPTS} to compare against, skipping the staleness check"
    return 0
  fi

  if ! command -v sha256sum >/dev/null 2>&1; then
    log_warn "sha256sum is not on PATH, skipping the staleness check"
    return 0
  fi

  local name baked mounted stale=()

  for name in $(script_names); do
    baked="$(file_digest "${IMAGE_SCRIPTS}/${name}")"
    mounted="$(file_digest "${REPO_SCRIPTS}/${name}")"

    if [[ -z "$baked" || -z "$mounted" ]]; then
      log_warn "could not hash ${name} on both sides, leaving it unjudged"
      continue
    fi

    if [[ "$baked" == "$mounted" ]]; then
      continue
    fi

    stale+=("$name")
  done

  if [[ "${#stale[@]}" -eq 0 ]]; then
    log_info "the baked scripts match ${REPO_SCRIPTS}"
    return 0
  fi

  report_stale "${stale[@]}"

  return 1
}

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
  if [[ "${SANDBOX_SKIP_UPDATE:-0}" == "1" ]]; then
    log_warn "SANDBOX_SKIP_UPDATE=1, keeping the versions baked into the image"
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
  if ! assert_scripts_are_fresh; then
    exit 3
  fi

  if ! trust_mounted_repo; then
    exit 2
  fi

  update_agents
  report_versions

  if [[ $# -eq 0 ]]; then
    exec /bin/bash
  fi

  exec "$@"
}

main "$@"
