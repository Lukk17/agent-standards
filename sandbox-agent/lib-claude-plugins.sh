#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: lib-claude-plugins.sh
# Description: The Claude Code plugin route, shared by setup-project.sh,
#              setup-global.sh, both verify scripts and
#              e2e-mock/subagent-write.sh. Serves the
#              branch the import reads from the mounted repository as a git
#              marketplace over smart HTTP on 127.0.0.1, with the repository's
#              own tools/git_http.py, because Claude Code refuses a file:// URL
#              and loads a local folder in place instead of copying each
#              plugin into its cache, where a consumer's plugins sit. Then runs
#              the three commands of docs/AGENT_TOOLING.md step 1 at project
#              scope, or the commands of the Claude Code section of
#              docs/GLOBAL_SETUP.md with the user scope. Nothing here reaches a
#              model or the network.
# Usage: sourced. The caller calls claude_market_stop from its EXIT trap. The
#        check helpers at the end read CLAUDE_PLUGINS and CLAUDE_CACHE and
#        call pass, fail and join_commas, all of which the verify script
#        that sources this file defines.
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
# The bundles the Claude Code section of docs/GLOBAL_SETUP.md installs for
# every project of one user: core, one domain, and every hook. None carries an
# MCP server.
readonly CLAUDE_USER_PLUGINS=(core review-and-security hooks-all)

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

# Adds the served marketplace for the user and installs CLAUDE_USER_PLUGINS
# with the user scope, which records both in the settings.json of the caller's
# configuration directory, CLAUDE_CONFIG_DIR or ~/.claude. The commands run
# from the start folder the caller names, and write nothing into it.
claude_plugins_install_user() {
  local start="$1" market="" plugin=""
  local settings="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}/settings.json"

  claude_plugin "$start" marketplace add "$CLAUDE_MARKET_URL" --scope user || return 1
  market="$(jq -r '.extraKnownMarketplaces | keys[0]' "$settings")" || return 1

  for plugin in "${CLAUDE_USER_PLUGINS[@]}"; do
    claude_plugin "$start" install "${plugin}@${market}" --scope user || return 1
  done
}

# Every plugin the named bundles install, from the catalog Claude Code cloned,
# one "<category> <name>" per line.
# Arguments: catalog file, then the bundle names.
claude_plugin_closure() {
  python3 -I -S - "$@" <<'PY'
import json
import sys

entries = {entry["name"]: entry for entry in json.load(open(sys.argv[1], encoding="utf-8"))["plugins"]}
seen, stack = set(), list(sys.argv[2:])

while stack:
    name = stack.pop()

    if name not in seen:
        seen.add(name)
        stack.extend(entries[name].get("dependencies", []))

for name in sorted(seen):
    print(entries[name]["category"], name)
PY
}

# Prints the hook wiring Claude Code runs from the hook plugins a settings file
# switches on: their hooks merged by event, in the shape a settings file holds
# them.
# Arguments: catalog file, settings file.
claude_plugin_wiring() {
  jq --slurpfile settings "$2" '
    ($settings[0].enabledPlugins // {}) as $on
    | .name as $market
    | {hooks: ([.plugins[] | select(.category == "hook" and $on["\(.name)@\($market)"] == true) | .hooks | to_entries[]]
        | group_by(.key) | map({key: .[0].key, value: (map(.value) | add)}) | from_entries)}' "$1"
}

# Passes when the jq filter over a file named in full returns true. The
# optional fourth argument is the name a failure reports the file by.
assert_json_at() {
  local label="$1" file="$2" filter="$3" name="${4:-$2}"
  local result=""

  if [[ ! -f "$file" ]]; then
    fail "${label} (${name} is missing)"
    return
  fi

  result="$(jq -r "$filter" "$file" 2>/dev/null || echo "error")"

  if [[ "$result" == "true" ]]; then
    pass "${label}"
  else
    fail "${label} (the check over ${name} returned '${result}')"
  fi
}

# Passes when two sorted lists, one name per line, are the same.
assert_same_names() {
  local label="$1" expected="$2" actual="$3"
  local count=0 missing="" extra=""

  count="$(grep -c . <<<"$expected" || true)"
  missing="$(comm -23 <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") | tr '\n' ' ')"
  extra="$(comm -13 <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") | tr '\n' ' ')"

  if [[ "$count" -gt 0 && -z "$missing" && -z "$extra" ]]; then
    pass "${label} (${count} of ${count})"
  else
    fail "${label} (missing: ${missing:-none}, not expected: ${extra:-none})"
  fi
}

# The names of one category in CLAUDE_PLUGINS, one per line.
claude_plugins_of() {
  local category="$1" line=""

  for line in "${CLAUDE_PLUGINS[@]}"; do
    [[ "$line" == "${category} "* ]] && printf '%s\n' "${line#* }"
  done

  return 0
}

# Counts the plugins of one category whose folder under CLAUDE_CACHE holds the
# file the pattern names, where @ stands for the plugin's item name and + for
# that name with an underscore for every dash, the way a hook script is named.
assert_claude_cache() {
  local label="$1" category="$2" prefix="$3" pattern="$4"
  local name="" item="" file="" found=0 total=0 missing=()
  local matches=()

  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    total=$((total + 1))
    item="${name#"$prefix"}"
    file="${pattern//@/$item}"
    file="${file//+/${item//-/_}}"
    shopt -s nullglob
    # shellcheck disable=SC2206
    matches=( ${CLAUDE_CACHE}/${name}/*/${file} )
    shopt -u nullglob

    if [[ "${#matches[@]}" -eq 1 ]]; then
      found=$((found + 1))
    else
      missing+=("$name")
    fi
  done < <(claude_plugins_of "$category")

  if [[ "$total" -gt 0 && "$found" -eq "$total" ]]; then
    pass "${label} (${found} of ${total})"
  else
    fail "${label} (${found} of ${total}, missing: $(join_commas "${missing[@]}"))"
  fi
}
