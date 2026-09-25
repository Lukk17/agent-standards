#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: opencode-family.sh
# Description: What OpenCode and Kilo Code share, sourced by opencode.sh and
#              kilo-code.sh after lib.sh. Both run the same engine, read the same
#              opencode.json and plugin, and export sessions in the same shape,
#              so only the binary and the config variable differ.
# Contract: the sourcing script sets AGENT_BIN and CONFIG_CONTENT_VAR (the
#           environment variable that carries inline configuration).
# -----------------------------------------------------------------------------
# shellcheck disable=SC2034  # contract variables read by lib.sh, which sources before this file

readonly WRITE_TOOL_RE='^(write|edit|patch|multiedit|apply_patch|bash)$'
readonly SPAWN_TOOL_RE='^task$'
readonly SKILL_TOOL_RE='^skill$'
readonly HEALTH_FORMAT="chat"
readonly GATE_KNOWN_GAP=0
readonly PROVIDER_ID="requesty"

# The provider travels in an environment variable, never in the committed
# opencode.json, and names the key by {env:} reference rather than carrying it.
agent_configure() {
  local config

  export XDG_CONFIG_HOME="${WORK}/xdg/config"
  export XDG_DATA_HOME="${WORK}/xdg/data"
  export XDG_STATE_HOME="${WORK}/xdg/state"
  export XDG_CACHE_HOME="${WORK}/xdg/cache"
  mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

  config="$(jq -cn --arg id "$PROVIDER_ID" --arg url "$PROVIDER_V1_URL" --arg m "$MODEL" '{
    provider: {($id): {
      npm: "@ai-sdk/openai-compatible",
      name: "Requesty",
      options: {baseURL: $url, apiKey: "{env:REQUESTY_API_KEY}"},
      models: {($m): {name: $m, tool_call: true}}
    }},
    model: ($id + "/" + $m),
    small_model: ($id + "/" + $m),
    autoupdate: false,
    share: "disabled"
  }')"

  export "${CONFIG_CONTENT_VAR}=${config}"
}

# Writes the sorted session ids of the current project to $1.
list_sessions() {
  local out="$1"

  "$AGENT_BIN" session list --format json > "${out}.json" 2>/dev/null || true
  jq -r '.[]?.id // empty' "${out}.json" 2>/dev/null | sort -u > "$out" || : > "$out"
}

# Every stream and export goes to a file, never through a pipe: OpenCode
# truncates a large stdout on a pipe. See sandbox-agent/README.md.
agent_invoke() {
  local dir="$1" prompt="$2" main_id="" child status=0

  list_sessions "${dir}/.sessions-before"

  timeout "$AGENT_TIMEOUT" "$AGENT_BIN" run --format json --auto \
    --model "${PROVIDER_ID}/${MODEL}" --dir "$PROJECT" "$prompt" \
    > "${dir}/stream.jsonl" 2> "${dir}/stderr.log" < /dev/null || status=$?

  main_id="$(jq -R -s -r '[split("\n")[] | fromjson? | .sessionID? // empty] | first // ""' "${dir}/stream.jsonl")"
  if [[ -z "$main_id" ]]; then
    log_info "no session id in the stream, nothing to export"
    return "$status"
  fi

  mkdir -p "${dir}/transcripts"
  "$AGENT_BIN" export "$main_id" > "${dir}/transcripts/main-${main_id}.json" 2>> "${dir}/stderr.log" || true

  list_sessions "${dir}/.sessions-after"
  {
    comm -13 "${dir}/.sessions-before" "${dir}/.sessions-after"
    jq -r '.. | objects | select(.type? == "tool" and .tool? == "task")
           | .state.metadata.sessionId? // .state.metadata.sessionID? // empty' \
      "${dir}/transcripts/main-${main_id}.json" 2>/dev/null || true
  } | sort -u | while IFS= read -r child; do
    [[ -n "$child" && "$child" != "$main_id" ]] || continue
    "$AGENT_BIN" export "$child" > "${dir}/transcripts/subagent-${child}.json" 2>> "${dir}/stderr.log" || true
  done

  return "$status"
}

agent_calls() {
  local dir="$1" file actor

  for file in "${dir}"/transcripts/*.json; do
    [[ -f "$file" ]] || continue
    actor="main"
    [[ "$(basename "$file")" == subagent-* ]] && actor="subagent"
    jq -c --arg actor "$actor" '
      .messages[]? | .parts[]? | select(.type == "tool")
      | {actor: $actor, tool: (.tool // ""), input: ((.state.input // {}) | tojson),
         result: ((.state.output // .state.error // "") | tostring),
         error: ((.state.status // "") == "error")}' "$file" 2>/dev/null || true
  done
}

# The shared plugin appends the reminder to every user message as a synthetic
# text part, so it has to sit in a user message of the main session.
agent_reminder_seen() {
  local dir="$1" file found

  for file in "${dir}"/transcripts/main-*.json; do
    [[ -f "$file" ]] || continue
    found="$(jq --arg r "$REMINDER_MARKER" '
      [.messages[]? | select(.info.role? == "user") | .parts[]? | select(.type == "text")
       | .text | select(contains($r))] | length' "$file" 2>/dev/null || echo 0)"
    [[ "$found" -gt 0 ]] && return 0
  done

  return 1
}

# Every child session the case started is exported as subagent-*.json, and the
# plugin puts the subagent text into that session's user message.
agent_subagent_context() {
  local dir="$1" file

  for file in "${dir}"/transcripts/subagent-*.json; do
    [[ -f "$file" ]] && cat -- "$file"
  done

  return 0
}
