#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: claude-code.sh
# Description: Runs Claude Code headless against Requesty (Anthropic
#              Messages format) and asserts on its stream-json tool calls, hook
#              events and subagent transcripts. See lib.sh for the contract.
# Usage: claude-code.sh [health|run|all] [-h|--help]
# Environment: REQUESTY_API_KEY plus the LIVE_* variables documented in lib.sh.
# Exit codes: as lib.sh.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# shellcheck source=sandbox-agent/live/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

readonly AGENT_LABEL="claude-code"
readonly AGENT_BIN="claude"
readonly AGENT_NPM_PACKAGE="@anthropic-ai/claude-code"
readonly HEALTH_FORMAT="anthropic"
readonly WRITE_TOOL_RE='^(Write|Edit|MultiEdit|NotebookEdit|Bash)$'
readonly SPAWN_TOOL_RE='^(Task|Agent)$'
readonly SKILL_TOOL_RE='^Skill$'
readonly GATE_KNOWN_GAP=0
readonly MAX_TURNS=15

agent_configure() {
  unset ANTHROPIC_API_KEY
  export CLAUDE_CONFIG_DIR="${WORK}/claude-config"
  export ANTHROPIC_BASE_URL="$PROVIDER_URL"
  export ANTHROPIC_AUTH_TOKEN="$REQUESTY_API_KEY"
  export ANTHROPIC_MODEL="$MODEL"
  export ANTHROPIC_DEFAULT_OPUS_MODEL="$MODEL"
  export ANTHROPIC_DEFAULT_SONNET_MODEL="$MODEL"
  export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL"
  export ANTHROPIC_SMALL_FAST_MODEL="$MODEL"
  export CLAUDE_CODE_SUBAGENT_MODEL="$MODEL"
  export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
  export DISABLE_AUTOUPDATER=1

  mkdir -p "$CLAUDE_CONFIG_DIR"
}

agent_invoke() {
  local dir="$1" prompt="$2" snapshot file role status=0

  snapshot="${dir}/.before"
  snapshot_files "${CLAUDE_CONFIG_DIR}/projects" "$snapshot"

  timeout "$AGENT_TIMEOUT" "$AGENT_BIN" -p "$prompt" \
    --output-format stream-json --verbose --include-hook-events \
    --dangerously-skip-permissions --max-turns "$MAX_TURNS" --model "$MODEL" \
    > "${dir}/stream.jsonl" 2> "${dir}/stderr.log" || status=$?

  mkdir -p "${dir}/transcripts"
  while IFS= read -r file; do
    [[ "$file" == *.jsonl ]] || continue
    role="main"
    [[ "$(basename "$(dirname "$file")")" == "subagents" ]] && role="subagent"
    cp -- "$file" "${dir}/transcripts/${role}-$(basename "$file")"
  done < <(new_files_since "${CLAUDE_CONFIG_DIR}/projects" "$snapshot")

  return "$status"
}

# One jq program reads both the stream and a sidechain transcript. A message
# with a parent_tool_use_id, or any line of a subagents/ transcript, is the
# subagent's own call. The stream and the session transcripts record the same
# tool_use, so agent_calls keeps the first record per tool_use id.
# shellcheck disable=SC2016  # $names here are jq variables, not shell expansions
readonly CALLS_FILTER='
  def text_of: if type == "string" then . elif type == "array" then (map(.text? // tostring) | join("\n")) else tostring end;
  (map(select(.type == "user") | (.message.content? // []) | if type == "array" then .[] else empty end
       | select(type == "object" and .type == "tool_result")
       | {key: .tool_use_id, value: {result: (.content | text_of), error: (.is_error // false)}})
   | from_entries) as $res
  | .[] | select(.type == "assistant") | (.parent_tool_use_id // null) as $parent
  | (.message.content? // []) | if type == "array" then .[] else empty end
  | select(type == "object" and .type == "tool_use")
  | {id: .id, actor: (if $force != "" then $force elif $parent != null then "subagent" else "main" end),
     tool: .name, input: (.input | tojson),
     result: ($res[.id].result // ""), error: ($res[.id].error // false)}'

agent_calls() {
  local dir="$1" file actor

  {
    jq -R -s -c --arg force "" "[split(\"\n\")[] | fromjson?] | ${CALLS_FILTER}" "${dir}/stream.jsonl"

    for file in "${dir}"/transcripts/*.jsonl; do
      [[ -f "$file" ]] || continue
      actor=""
      [[ "$(basename "$file")" == subagent-* ]] && actor="subagent"
      jq -R -s -c --arg force "$actor" "[split(\"\n\")[] | fromjson?] | ${CALLS_FILTER}" "$file"
    done
  } | jq -s -c 'foreach .[] as $call ({}; .[$call.id] += 1; if .[$call.id] == 1 then $call | del(.id) else empty end)'
}

# SessionStart echoes the same text, so only a UserPromptSubmit hook event, in
# the stream or in the session transcript, counts as the per-prompt reminder.
agent_reminder_seen() {
  local dir="$1" found

  found="$(cat "${dir}/stream.jsonl" "${dir}"/transcripts/*.jsonl 2>/dev/null |
    jq -R -s --arg r "$REMINDER_MARKER" '
      [ split("\n")[] | fromjson? | .. | objects
        | select(((.hook_event? // .hookEvent? // .hook_name? // .hookName? // "") | tostring | test("UserPromptSubmit")))
        | select(tostring | contains($r)) ] | length')"

  [[ "$found" -gt 0 ]]
}

# A subagent's sidechain transcript sits under subagents/ and is copied as
# subagent-*.jsonl, so those files alone are the subagent's recorded context.
agent_subagent_context() {
  local dir="$1" file

  for file in "${dir}"/transcripts/subagent-*.jsonl; do
    [[ -f "$file" ]] && cat -- "$file"
  done

  return 0
}

live_main "$@"
