#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: copilot.sh
# Description: Runs the GitHub Copilot CLI headless with bring-your-own-key
#              against OpenAI's own API (Responses format) and
#              asserts on its JSONL events. Offline mode keeps it off GitHub's
#              servers, so no GitHub token is involved.
# Usage: copilot.sh [health|run|all] [-h|--help]
# Environment: OPENAI_API_KEY plus the LIVE_* variables documented in lib.sh.
# Exit codes: as lib.sh.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly AGENT_PROVIDER="openai"
readonly AGENT_MODEL="gpt-6-luna"

# shellcheck source=sandbox-agent/live/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

readonly AGENT_LABEL="copilot"
readonly AGENT_BIN="copilot"
readonly AGENT_NPM_PACKAGE="@github/copilot"
readonly HEALTH_FORMAT="responses"
readonly WRITE_TOOL_RE='^(create|edit|write|str_replace_editor|apply_patch|bash|powershell)$'
readonly SPAWN_TOOL_RE='^task$'
readonly SKILL_TOOL_RE='^skill$'
readonly GATE_KNOWN_GAP=1
readonly PROMPT_TOKENS=128000
readonly OUTPUT_TOKENS=8192

agent_configure() {
  export COPILOT_HOME="${WORK}/copilot-home"
  export COPILOT_OFFLINE=true
  export COPILOT_AUTO_UPDATE=false
  export COPILOT_PROVIDER_TYPE=openai
  export COPILOT_PROVIDER_WIRE_API=responses
  export COPILOT_PROVIDER_BASE_URL="$PROVIDER_V1_URL"
  export COPILOT_PROVIDER_API_KEY="${!PROVIDER_KEY_VAR}"
  export COPILOT_PROVIDER_MAX_PROMPT_TOKENS="$PROMPT_TOKENS"
  export COPILOT_PROVIDER_MAX_OUTPUT_TOKENS="$OUTPUT_TOKENS"
  export COPILOT_MODEL="$MODEL"
  export COPILOT_ALLOW_ALL=true
  export GITHUB_COPILOT_PROMPT_MODE_REPO_HOOKS=true

  mkdir -p "$COPILOT_HOME"
  jq -n --arg p "$PROJECT" '{trustedFolders: [$p]}' > "${COPILOT_HOME}/config.json"
}

agent_invoke() {
  local dir="$1" prompt="$2" snapshot file status=0

  snapshot="${dir}/.before"
  snapshot_files "${COPILOT_HOME}/session-state" "$snapshot"

  timeout "$AGENT_TIMEOUT" "$AGENT_BIN" -p "$prompt" --output-format json \
    --allow-all --no-ask-user --log-dir "${dir}/logs" \
    > "${dir}/stream.jsonl" 2> "${dir}/stderr.log" < /dev/null || status=$?

  mkdir -p "${dir}/transcripts"
  while IFS= read -r file; do
    [[ "$file" == *.jsonl ]] || continue
    cp -- "$file" "${dir}/transcripts/$(basename "$(dirname "$file")")-$(basename "$file")"
  done < <(new_files_since "${COPILOT_HOME}/session-state" "$snapshot")

  return "$status"
}

# A tool call that carries a parent tool call id ran inside a subagent. The
# stream and the session-state log repeat the same events, so calls are
# deduplicated by their id.
agent_calls() {
  local dir="$1"

  cat "${dir}/stream.jsonl" "${dir}"/transcripts/*.jsonl 2>/dev/null | jq -R -s -c '
    [split("\n")[] | fromjson? | select(type == "object")] as $events
    | ($events | map(select(.type == "tool.execution_complete") | .data
        | {key: (.toolCallId // ""),
           value: {result: ((.result.content // .result // .error.message // .error // "") | tostring),
                   error: ((.success // true) | not)}}) | from_entries) as $res
    | $events | map(select(.type == "tool.execution_start") | .data) | unique_by(.toolCallId) | .[]
    | {actor: (if (.parentToolCallId // null) != null then "subagent" else "main" end),
       tool: (.toolName // ""),
       input: ((.arguments // {}) | if type == "string" then . else tojson end),
       result: ($res[.toolCallId // ""].result // ""),
       error: ($res[.toolCallId // ""].error // false)}'
}

# sessionStart injects the same text once, so the proof of the per-prompt
# hook is the reminder sitting in the same string as this prompt's nonce.
agent_reminder_seen() {
  local dir="$1" nonce="$2" found

  found="$(cat "${dir}/stream.jsonl" "${dir}"/transcripts/*.jsonl 2>/dev/null |
    jq -R -s --arg r "$REMINDER_MARKER" --arg n "$nonce" '
      [split("\n")[] | fromjson? | .. | strings | select(contains($r) and contains($n))] | length')"

  [[ "$found" -gt 0 ]]
}

# An event carrying a parent tool call id, or a subagent lifecycle event,
# belongs to a subagent. The stream and the session-state log repeat events.
agent_subagent_context() {
  local dir="$1"

  cat "${dir}/stream.jsonl" "${dir}"/transcripts/*.jsonl 2>/dev/null | jq -R -s -c '
    [split("\n")[] | fromjson? | objects
     | select(((.data.parentToolCallId? // null) != null) or ((.type // "") | tostring | startswith("subagent")))]
    | unique | .[]'
}

# Copilot ends a session whose model request the provider rejected with a
# session.error event. The stream and the session-state log repeat it.
agent_model_error() {
  local dir="$1" error

  error="$(cat "${dir}/stream.jsonl" "${dir}"/transcripts/*.jsonl 2>/dev/null | jq -R -s -r '
    [split("\n")[] | fromjson? | objects | select(.type == "session.error") | .data.message // empty]
    | unique | join("; ")')"

  [[ -n "$error" ]] || return 1
  printf '%s\n' "$error"
}

live_main "$@"
