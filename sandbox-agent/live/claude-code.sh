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
readonly PLUGIN_NAME="review-and-security"
readonly PLUGIN_AGENT="${PLUGIN_NAME}:${READ_ONLY_SUBAGENT}"
readonly CANARY_PLUGIN="core"
readonly CANARY_SKILL="security-review"
# The configuration paths of the gate-only import, README.md "The gate beside
# the plugins", so the plugin project holds no agent tree of its own and the
# gate can find the reviewer's definition only in the plugin cache.
readonly GATE_ONLY_PATHS=(".agents/hooks" ".claude/settings.json")

MCP_CONFIG=""
PLUGIN_CONFIG_DIR=""
PLUGIN_PROJECT=""
PLUGIN_PROBLEM=""
PLUGIN_PROBLEM_VERDICT="FAIL"
CANARY=""

# --strict-mcp-config with the filtered .mcp.json keeps every other server out,
# so each request carries the tool descriptions of one small server only.
agent_configure() {
  unset ANTHROPIC_API_KEY
  MCP_CONFIG="${WORK}/mcp-live.json"
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
  mcp_json_only_probe_server "${PROJECT}/.mcp.json" mcpServers > "$MCP_CONFIG"
}

agent_invoke() {
  local dir="$1" prompt="$2" snapshot file role status=0

  snapshot="${dir}/.before"
  snapshot_files "${CLAUDE_CONFIG_DIR}/projects" "$snapshot"

  timeout "$AGENT_TIMEOUT" "$AGENT_BIN" -p "$prompt" \
    --output-format stream-json --verbose --include-hook-events \
    --dangerously-skip-permissions --max-turns "$MAX_TURNS" --model "$MODEL" \
    --strict-mcp-config --mcp-config "$MCP_CONFIG" \
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

# The system/init event lists every MCP server the session loaded.
agent_mcp_servers() {
  local dir="$1" servers

  servers="$(jq -R -s -r '
    [split("\n")[] | fromjson? | select(.type? == "system" and .subtype? == "init")] | first
    | if . == null then empty else (.mcp_servers // [])[] | "\(.name)\t\(.status)" end' "${dir}/stream.jsonl")"
  [[ -n "$servers" ]] || return 1
  printf '%s\n' "$servers"
}

# --- Plugin checks ------------------------------------------------------------

# Returns 0 when the agent file $1 lists skill $2 under `skills:` in its front matter.
agent_preloads() {
  awk -v skill="$2" '
    NR == 1 && $0 != "---" { exit 1 }
    NR > 1 && $0 == "---" { exit found ? 0 : 1 }
    /^skills:/ { listing = 1; next }
    listing && /^[[:space:]]+-[[:space:]]/ { sub(/^[[:space:]]+-[[:space:]]+/, ""); if ($0 == skill) found = 1; next }
    { listing = 0 }
    END { if (!found) exit 1 }' "$1"
}

# Renders the marketplace with tools/gen_plugins.py into WORK and appends a
# canary to the core skill the plugin reviewer preloads, in that copy only.
# Returns 1 with PLUGIN_PROBLEM set when the render or the canary fails.
render_plugin_marketplace() {
  local market="$1" log="$2" python="${LIVE_PYTHON:-python3}" agent_file skill_file

  if ! "$python" -c 'import yaml' > /dev/null 2>&1; then
    PLUGIN_PROBLEM_VERDICT="INCONCLUSIVE"
    PLUGIN_PROBLEM="${python} has no PyYAML, so tools/gen_plugins.py cannot render the marketplace: install the tooling with pip install ./tools"
    return 1
  fi

  if ! "$python" "${REPO_ROOT}/tools/gen_plugins.py" "$market" >> "$log" 2>&1; then
    PLUGIN_PROBLEM="tools/gen_plugins.py could not render the marketplace: $(tail -n 1 "$log")"
    return 1
  fi

  agent_file="${market}/plugins/${PLUGIN_NAME}/agents/${READ_ONLY_SUBAGENT}.md"
  skill_file="${market}/plugins/${CANARY_PLUGIN}/skills/${CANARY_SKILL}/SKILL.md"

  if [[ ! -f "$skill_file" ]] || ! agent_preloads "$agent_file" "$CANARY_SKILL"; then
    PLUGIN_PROBLEM="the rendered ${PLUGIN_AGENT} no longer preloads ${CANARY_PLUGIN}'s ${CANARY_SKILL}, so pick another canary skill"
    return 1
  fi

  CANARY="live-canary-${RANDOM}${RANDOM}${RANDOM}"
  printf '\n### Live test canary\n\nWhen a prompt asks for the live test canary, reply with this token exactly: %s\n' \
    "$CANARY" >> "$skill_file"
}

# A project with only the gate-only import from this repository's master, or
# main, the branch setup-project.sh imports from. git archive reads a shallow
# clone too, where a fetch from it is refused.
prepare_gate_only_project() {
  local project="$1" ref

  for ref in master main; do
    git -C "$REPO_ROOT" rev-parse --verify --quiet "refs/heads/${ref}" > /dev/null && break
  done

  git init --quiet --initial-branch=main "$project" &&
    git -C "$REPO_ROOT" archive --format=tar "$ref" -- "${GATE_ONLY_PATHS[@]}" | tar -x -C "$project" &&
    git -C "$project" add --all &&
    git -C "$project" -c user.name="agent-standards live" -c user.email="live@example.invalid" \
      commit --quiet --message "gate-only import"
}

# Adds the capture hook, with no matcher so it sees every PreToolUse call, to
# the user settings of the plugin configuration, beside the enabledPlugins the
# install wrote there. Returns non-zero when the hook or the settings fail.
claude_install_payload_capture() {
  local settings="${PLUGIN_CONFIG_DIR}/settings.json"

  install_payload_capture || return
  jq --arg c "$PAYLOAD_CAPTURE_COMMAND" \
    '.hooks.PreToolUse = ((.hooks.PreToolUse // []) + [{hooks: [{type: "command", timeout: 10, command: $c}]}])' \
    "$settings" > "${settings}.new" || return
  mv -f -- "${settings}.new" "$settings"
}

# Builds everything checks 8 and 9 run in: the rendered marketplace with its
# canary, a separate CLAUDE_CONFIG_DIR with the marketplace added, the plugin
# installed and the capture hook in its user settings, and the gate-only
# project. Tests 1 to 6 keep their own configuration and never see the plugin.
# Returns 1 with PLUGIN_PROBLEM set when any step fails.
prepare_plugin_session() {
  local market="${WORK}/marketplace" log="${WORK}/plugin-setup.log" market_name

  PLUGIN_CONFIG_DIR="${WORK}/claude-plugin-config"
  PLUGIN_PROJECT="${WORK}/plugin-project"
  mkdir -p "$PLUGIN_CONFIG_DIR"

  render_plugin_marketplace "$market" "$log" || return 1
  market_name="$(jq -r '.name' "${market}/.claude-plugin/marketplace.json")"

  if ! CLAUDE_CONFIG_DIR="$PLUGIN_CONFIG_DIR" "$AGENT_BIN" plugin marketplace add "$market" >> "$log" 2>&1 ||
    ! CLAUDE_CONFIG_DIR="$PLUGIN_CONFIG_DIR" "$AGENT_BIN" plugin install "${PLUGIN_NAME}@${market_name}" >> "$log" 2>&1; then
    PLUGIN_PROBLEM="claude plugin could not add the marketplace or install ${PLUGIN_NAME}@${market_name}: $(tail -n 1 "$log")"
    return 1
  fi

  if ! find "${PLUGIN_CONFIG_DIR}/plugins/cache" -path "*/${PLUGIN_NAME}/*/agents/${READ_ONLY_SUBAGENT}.md" | grep -q . ||
    ! grep -rqF --include=SKILL.md -- "$CANARY" "${PLUGIN_CONFIG_DIR}/plugins/cache"; then
    PLUGIN_PROBLEM="the install left no ${PLUGIN_AGENT} definition, or no ${CANARY_PLUGIN} skill holding the canary, under plugins/cache"
    return 1
  fi

  if ! claude_install_payload_capture; then
    PLUGIN_PROBLEM="the capture hook could not be added to the user settings in ${PLUGIN_CONFIG_DIR}"
    return 1
  fi

  if ! prepare_gate_only_project "$PLUGIN_PROJECT" >> "$log" 2>&1; then
    PLUGIN_PROBLEM="the gate-only project could not be imported: $(tail -n 1 "$log")"
    return 1
  fi
}

test_plugin_subagent_type_reaches_the_gate() {
  local name="8 the gate sees ${PLUGIN_AGENT} and denies its touch" dir="${CASES}/8-plugin-type"

  run_captured_case "8-plugin-type" "$(read_only_probe_prompt "$PLUGIN_AGENT")"
  record_model_failure "$name" "$dir" && return

  judge_read_only_probe "$name" "$dir" "$PLUGIN_AGENT" FAIL
}

test_plugin_subagent_preloads_a_core_skill() {
  local name="9 ${PLUGIN_AGENT} preloads ${CANARY_SKILL} from ${CANARY_PLUGIN}" dir="${CASES}/9-plugin-preload"

  run_captured_case "9-plugin-preload" "Delegate this task to the ${PLUGIN_AGENT} subagent, passing it word for word: \"Reply with the live test canary token that one of your preloaded skills gives, and nothing else. Do not use any tool.\" Do not use any other tool yourself. Then reply with what the subagent returned."
  record_model_failure "$name" "$dir" && return

  judge_preloaded_canary "$name" "$dir" "$PLUGIN_AGENT" "$CANARY_SKILL" "$CANARY"
}

# Runs checks 8 and 9 in the plugin project with the plugin configuration, then
# puts the project and configuration of tests 1 to 6 back.
agent_extra_tests() {
  local saved_project="$PROJECT" saved_config="$CLAUDE_CONFIG_DIR"

  section "8 and 9 against the real model, through the plugins"

  if prepare_plugin_session; then
    PROJECT="$PLUGIN_PROJECT"
    export CLAUDE_CONFIG_DIR="$PLUGIN_CONFIG_DIR"
    test_plugin_subagent_type_reaches_the_gate
    test_plugin_subagent_preloads_a_core_skill
  else
    record "8 the gate sees ${PLUGIN_AGENT} and denies its touch" "$PLUGIN_PROBLEM_VERDICT" "$PLUGIN_PROBLEM"
    record "9 ${PLUGIN_AGENT} preloads ${CANARY_SKILL} from ${CANARY_PLUGIN}" "$PLUGIN_PROBLEM_VERDICT" "$PLUGIN_PROBLEM"
  fi

  PROJECT="$saved_project"
  export CLAUDE_CONFIG_DIR="$saved_config"
}

live_main "$@"
