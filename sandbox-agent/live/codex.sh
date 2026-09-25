#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: codex.sh
# Description: Runs Codex headless against OpenAI's own API (Responses format)
#              and asserts on the rollout files it records for the main thread
#              and for every subagent thread. See lib.sh for the contract.
# Usage: codex.sh [health|run|all] [-h|--help]
# Environment: OPENAI_API_KEY plus the LIVE_* variables documented in lib.sh.
# Exit codes: as lib.sh.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly AGENT_PROVIDER="openai"
readonly AGENT_MODEL="gpt-6-luna"

# shellcheck source=sandbox-agent/live/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

readonly AGENT_LABEL="codex"
readonly AGENT_BIN="codex"
readonly AGENT_NPM_PACKAGE="@openai/codex"
readonly HEALTH_FORMAT="responses"
readonly WRITE_TOOL_RE='^(apply_patch|shell|shell_command|exec_command|local_shell_call|write_stdin)$'
readonly SPAWN_TOOL_RE='^spawn_agent$'
readonly SKILL_TOOL_RE='^(skill|load_skill)$'
readonly GATE_KNOWN_GAP=0
readonly MCP_STARTUP_TIMEOUT_SEC=60

MCP_ARGS=()

# Prints every [mcp_servers.*] name in a Codex config.toml except MCP_SERVER.
codex_other_mcp_servers() {
  python3 -S -E - "$1" "$MCP_SERVER" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    servers = tomllib.load(handle).get("mcp_servers", {})

for name in sorted(servers):
    if name != sys.argv[2]:
        print(name)
PY
}

# CODEX_HOME is CI-only and throwaway: it carries the provider, which names the
# key's environment variable rather than the key, and trusts the one project so
# Codex reads the imported .codex/ layer. Codex reserves the provider id openai
# for its login-based built-in, so the key-based provider needs its own id.
# Every imported MCP server but MCP_SERVER is switched off with a --config
# override, which outranks the project layer, and the startup grace of 0 makes
# Codex wait for the npx-started server before it builds the first tool list.
agent_configure() {
  local name

  export CODEX_HOME="${WORK}/codex-home"
  mkdir -p "$CODEX_HOME"

  MCP_ARGS=(-c "mcp_servers.${MCP_SERVER}.startup_timeout_sec=${MCP_STARTUP_TIMEOUT_SEC}")
  while IFS= read -r name; do
    [[ -n "$name" ]] && MCP_ARGS+=(-c "mcp_servers.${name}.enabled=false")
  done < <(codex_other_mcp_servers "${PROJECT}/.codex/config.toml")

  cat > "${CODEX_HOME}/config.toml" <<EOF
model = "${MODEL}"
model_provider = "openai-api"
model_supports_reasoning_summaries = false
mcp_optional_startup_grace_ms = 0

[model_providers.openai-api]
name = "OpenAI"
base_url = "${PROVIDER_V1_URL}"
env_key = "${PROVIDER_KEY_VAR}"
wire_api = "responses"

[projects."${PROJECT}"]
trust_level = "trusted"
EOF
}

agent_invoke() {
  local dir="$1" prompt="$2" snapshot file status=0

  snapshot="${dir}/.before"
  snapshot_files "${CODEX_HOME}/sessions" "$snapshot"

  timeout "$AGENT_TIMEOUT" "$AGENT_BIN" exec --json "${MCP_ARGS[@]}" \
    --dangerously-bypass-approvals-and-sandbox --dangerously-bypass-hook-trust \
    --cd "$PROJECT" "$prompt" \
    > "${dir}/stream.jsonl" 2> "${dir}/stderr.log" < /dev/null || status=$?

  mkdir -p "${dir}/transcripts"
  while IFS= read -r file; do
    cp -- "$file" "${dir}/transcripts/$(basename "$file")"
  done < <(new_files_since "${CODEX_HOME}/sessions" "$snapshot")

  return "$status"
}

# A rollout whose first session_meta names a subagent source belongs to a
# spawned agent, every other rollout is the main thread. In code mode every
# call is a custom_tool_call named exec whose input is a script calling
# tools.<name>(...), so each tool the script names becomes its own record.
# shellcheck disable=SC2016  # $names here are jq variables, not shell expansions
readonly CALLS_FILTER='
  def text_of: if type == "string" then . elif type == "array" then (map(.text? // tostring) | join("\n")) else tojson end;
  (first(.[] | select(.type == "session_meta") | .payload.source) // "exec") as $source
  | (if ($source | tostring | test("subagent"; "i")) then "subagent" else "main" end) as $actor
  | ([.[] | select(.type == "response_item") | .payload
      | select(.type == "function_call_output" or .type == "custom_tool_call_output")
      | {key: (.call_id // ""), value: (.output | text_of)}] | from_entries) as $out
  | .[] | select(.type == "response_item") | .payload
  | select(.type == "function_call" or .type == "custom_tool_call" or .type == "local_shell_call")
  | ((.arguments // .input // .action // "") | if type == "string" then . else tojson end | gsub("\\\\+"; "/")) as $input
  | ($out[.call_id // ""] // "") as $result
  | (if .name == "exec" then [$input | scan("tools\\.([A-Za-z_]+)\\(") | .[0]] | unique else [] end) as $inner
  | {id: (.call_id // ""), actor: $actor,
     tool: (if ($inner | length) > 0 then $inner[] else (.name // .type) end),
     input: $input, result: $result,
     error: ($result | test("PREFLIGHT: |Script failed|^unsupported call: |\"exit_code\": ?[1-9]|Exit code: [1-9]"))}'

# A forked subagent rollout replays the parent history with the same call ids,
# so a call recorded in more than one rollout keeps its main-thread record.
readonly DEDUPE_FILTER='
  map(select(.id == "")) + (map(select(.id != "")) | group_by([.id, .tool]) | map(sort_by(.actor != "main") | first))
  | .[] | del(.id)'

# The exec stream reports every MCP tool call of the main thread as its own
# mcp_tool_call item, whatever shape the rollout gives the same call.
# shellcheck disable=SC2016  # $names here are jq variables, not shell expansions
readonly MCP_CALLS_FILTER='
  def text_of: if type == "string" then . elif type == "array" then (map(.text? // tostring) | join("\n")) else tojson end;
  .[] | select(.type? == "item.completed" and .item.type? == "mcp_tool_call") | .item
  | {id: "", actor: "main", tool: "mcp__\(.server)__\(.tool)",
     input: ((.arguments // {}) | if type == "string" then . else tojson end),
     result: ((.result.content // .error.message // "") | text_of),
     error: ((.status // "") == "failed" or (.error // null) != null)}'

agent_calls() {
  local dir="$1" file

  {
    for file in "${dir}"/transcripts/*.jsonl; do
      [[ -f "$file" ]] || continue
      jq -R -s -c "[split(\"\n\")[] | fromjson?] | ${CALLS_FILTER}" "$file"
    done
    [[ -f "${dir}/stream.jsonl" ]] && jq -R -s -c "[split(\"\n\")[] | fromjson?] | ${MCP_CALLS_FILTER}" "${dir}/stream.jsonl"
  } | jq -s -c "$DEDUPE_FILTER"
}

# The rollout does not record which MCP servers loaded, so the list comes from
# Codex itself, asked with the same overrides in the project the case ran in.
agent_mcp_servers() {
  local dir="$1"

  (cd "$PROJECT" && "$AGENT_BIN" "${MCP_ARGS[@]}" mcp list --json) > "${dir}/mcp-list.json" 2>> "${dir}/stderr.log" || return 1
  jq -r '.[] | select(.enabled) | "\(.name)\tenabled"' "${dir}/mcp-list.json"
}

# Codex hands a hook's additionalContext to the model as a developer message,
# while the imported AGENTS.md, which quotes the reminder, arrives as a user
# message, so only developer messages count as hook text.
readonly HOOK_TEXT_FILTER='select(.type == "response_item" and .payload.type? == "message" and .payload.role? == "developer")'

# Codex injects the reminder only through UserPromptSubmit on the main thread
# (SubagentStart carries the subagent text), so its text in a main rollout is the proof.
agent_reminder_seen() {
  local dir="$1" file source

  for file in "${dir}"/transcripts/*.jsonl; do
    [[ -f "$file" ]] || continue
    source="$(jq -R -s -r '[split("\n")[] | fromjson? | select(.type == "session_meta") | .payload.source | tostring] | first // ""' "$file")"
    [[ "${source,,}" == *subagent* ]] && continue
    jq -R -s -e --arg r "$REMINDER_MARKER" \
      "[split(\"\n\")[] | fromjson? | objects | ${HOOK_TEXT_FILTER} | tojson | select(contains(\$r))] | length > 0" \
      "$file" > /dev/null && return 0
  done

  return 1
}

# A subagent rollout can replay the parent history, the main-thread reminder
# included, so a line that a main rollout also holds, timestamps aside, is the
# parent's and is left out.
agent_subagent_context() {
  local dir="$1" file source seen
  local -a subagent_files=()

  seen="${dir}/.main-lines"

  : > "$seen"
  for file in "${dir}"/transcripts/*.jsonl; do
    [[ -f "$file" ]] || continue
    source="$(jq -R -s -r '[split("\n")[] | fromjson? | select(.type == "session_meta") | .payload.source | tostring] | first // ""' "$file")"
    if [[ "${source,,}" == *subagent* ]]; then
      subagent_files+=("$file")
    else
      jq -R -c 'fromjson? | objects | del(.timestamp)' "$file" >> "$seen"
    fi
  done

  for file in "${subagent_files[@]}"; do
    jq -R -s -c --slurpfile main "$seen" '
      [split("\n")[] | fromjson? | objects] | .[]
      | select(del(.timestamp) as $line | any($main[]; . == $line) | not)
      | '"${HOOK_TEXT_FILTER}" "$file"
  done
}

live_main "$@"
