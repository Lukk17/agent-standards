#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: lib-claude-plugins.sh
# Description: The Claude Code plugin route of a consumer project, shared by
#              setup-project.sh and e2e-mock/subagent-write.sh. Serves the
#              branch the import reads from the mounted repository as a git
#              marketplace over smart HTTP on 127.0.0.1, with the repository's
#              own tools/git_http.py, because Claude Code refuses a file:// URL
#              and loads a local folder in place instead of copying each
#              plugin into its cache, where a consumer's plugins sit. Then runs
#              the three commands of docs/AGENT_TOOLING.md step 1 at project
#              scope. Nothing here reaches a model or the network.
# Usage: sourced. The caller calls claude_market_stop from its EXIT trap.
# Environment:
#   SANDBOX_CLAUDE_MARKET_PORT  Port the marketplace is served on. Default
#                               49612. Fixed, so the address a project's
#                               .claude/settings.json records stays the same
#                               from one script to the next.
# -----------------------------------------------------------------------------

readonly CLAUDE_MARKET_PORT="${SANDBOX_CLAUDE_MARKET_PORT:-49612}"
readonly CLAUDE_MARKET_REPOSITORY="marketplace.git"
readonly CLAUDE_MARKET_URL="http://127.0.0.1:${CLAUDE_MARKET_PORT}/${CLAUDE_MARKET_REPOSITORY}"
readonly CLAUDE_MARKET_BRANCHES=(master main)
readonly CLAUDE_PLUGIN_TIMEOUT="${SANDBOX_CLI_TIMEOUT:-300}"
# The bundles docs/AGENT_TOOLING.md step 1 installs: core with every
# development domain, and every hook.
readonly CLAUDE_PROJECT_PLUGINS=(all hooks-all)

CLAUDE_MARKET_TMP=""
CLAUDE_MARKET_PID=""

# Echoes the branch of the repository the import reads, master before main.
claude_market_branch() {
  local repo="$1" branch=""

  for branch in "${CLAUDE_MARKET_BRANCHES[@]}"; do
    if git -C "$repo" rev-parse --verify --quiet "refs/heads/${branch}" >/dev/null; then
      printf '%s\n' "$branch"
      return 0
    fi
  done

  return 1
}

# Serves the committed tree of that branch at CLAUDE_MARKET_URL and waits until
# the port accepts a connection. Returns 1 when the branch, the server script
# or the port is missing.
claude_market_start() {
  local repo="$1" branch="" attempt=0

  [[ -z "$CLAUDE_MARKET_PID" ]] || return 0
  branch="$(claude_market_branch "$repo")" || return 1
  CLAUDE_MARKET_TMP="$(mktemp -d -t sandbox-claude-market-XXXXXXXX)"

  git clone --quiet --bare --single-branch --branch "$branch" "$repo" \
    "${CLAUDE_MARKET_TMP}/serve/${CLAUDE_MARKET_REPOSITORY}" >"${CLAUDE_MARKET_TMP}/server.log" 2>&1 || return 1

  python3 "${repo}/tools/git_http.py" "${CLAUDE_MARKET_TMP}/serve" --port "$CLAUDE_MARKET_PORT" \
    >>"${CLAUDE_MARKET_TMP}/server.log" 2>&1 &
  CLAUDE_MARKET_PID=$!

  while [[ "$attempt" -lt 100 ]]; do
    if (exec 3<>"/dev/tcp/127.0.0.1/${CLAUDE_MARKET_PORT}") 2>/dev/null; then
      return 0
    fi

    kill -0 "$CLAUDE_MARKET_PID" 2>/dev/null || return 1
    attempt=$((attempt + 1))
    sleep 0.1
  done

  return 1
}

claude_market_stop() {
  if [[ -n "$CLAUDE_MARKET_PID" ]]; then
    kill "$CLAUDE_MARKET_PID" 2>/dev/null || true
    wait "$CLAUDE_MARKET_PID" 2>/dev/null || true
    CLAUDE_MARKET_PID=""
  fi

  if [[ -n "$CLAUDE_MARKET_TMP" ]]; then
    rm -rf "$CLAUDE_MARKET_TMP"
    CLAUDE_MARKET_TMP=""
  fi
}

# Runs one `claude plugin` command from a project, with stdin closed so it
# cannot wait on a prompt, and bounded so a hang cannot use up the run.
claude_plugin() {
  local project="$1"
  shift

  (cd "$project" && NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" \
    DISABLE_AUTOUPDATER=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    timeout "$CLAUDE_PLUGIN_TIMEOUT" claude plugin "$@" </dev/null)
}

# Adds the served marketplace to a project and installs CLAUDE_PROJECT_PLUGINS
# into it, all at project scope, which records both in the project's
# .claude/settings.json. The plugin files land in the configuration directory
# of the caller, CLAUDE_CONFIG_DIR or ~/.claude.
claude_plugins_install() {
  local project="$1" market="" plugin=""

  claude_plugin "$project" marketplace add "$CLAUDE_MARKET_URL" --scope project || return 1
  market="$(jq -r '.extraKnownMarketplaces | keys[0]' "${project}/.claude/settings.json")" || return 1

  for plugin in "${CLAUDE_PROJECT_PLUGINS[@]}"; do
    claude_plugin "$project" install "${plugin}@${market}" --scope project || return 1
  done
}
