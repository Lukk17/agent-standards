#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: lib-opencode2.sh
# Description: OpenCode 2.x assertions shared by verify-project.sh and
#              verify-global.sh. Runs real 2.x turns against the stdlib mock
#              model in mock-model.mjs, so the gate, the plugin load and the
#              reply rules are measured on 2.x itself without credentials.
#              Also holds verify_reply_style_v1 and verify_start_folder_v1,
#              the same mock driving real OpenCode 1.x and Kilo Code turns.
# Usage: sourced. The caller defines pass, fail, note, one_line and
#        CLI_TIMEOUT, and calls opencode2_end from its EXIT trap.
# -----------------------------------------------------------------------------

OPENCODE2_MOCK="$(dirname "${BASH_SOURCE[0]}")/mock-model.mjs"
readonly OPENCODE2_MOCK
readonly OPENCODE2_MOCK_PORT="${SANDBOX_MOCK_PORT:-49611}"
readonly OPENCODE2_MODEL="sandbox/sandbox-model"
# A subagent whose definition names no model, so it runs on the mock too.
readonly OPENCODE2_SUBAGENT="docs-architect"
readonly OPENCODE2_DATABASE="${OPENCODE2_DATA_HOME:-${HOME}/.local/share/opencode-v2}/opencode/opencode.db"
readonly OPENCODE2_GATE_TEXT="PREFLIGHT: the main thread may not write files directly"
readonly OPENCODE2_PLUGIN_WARN="configured plugin path must be a directory"
readonly OPENCODE2_V1_REFUSAL="Database is not empty"
readonly OPENCODE2_GUARD_LOG="${SANDBOX_MCP_GUARD_LOG:-/tmp/sandbox-mcp-guard.log}"

OPENCODE2_TMP=""
OPENCODE2_MOCK_PID=""

# The provider block every 2.x probe directory carries, in the shape
# https://opencode.ai/v2/docs/providers/ documents for a custom provider.
opencode2_providers() {
  jq -n --arg url "http://127.0.0.1:${OPENCODE2_MOCK_PORT}/v1" '{
    sandbox: {
      name: "Sandbox",
      env: ["SANDBOX_MODEL_KEY"],
      package: "@opencode/ai/providers/openai-compatible",
      settings: { baseURL: $url },
      models: { "sandbox-model": { name: "Sandbox model" } }
    }
  }'
}

# Starts the mock model and waits until it accepts a connection.
opencode2_begin() {
  local attempt=0

  OPENCODE2_TMP="$(mktemp -d -t sandbox-opencode2-XXXXXXXX)"
  : >"${OPENCODE2_TMP}/requests.jsonl"

  node "$OPENCODE2_MOCK" "$OPENCODE2_MOCK_PORT" "${OPENCODE2_TMP}/requests.jsonl" \
    >"${OPENCODE2_TMP}/mock.log" 2>&1 &
  OPENCODE2_MOCK_PID=$!

  while [[ "$attempt" -lt 50 ]]; do
    if (exec 3<>"/dev/tcp/127.0.0.1/${OPENCODE2_MOCK_PORT}") 2>/dev/null; then
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 0.1
  done

  return 1
}

opencode2_end() {
  if [[ -n "$OPENCODE2_MOCK_PID" ]]; then
    kill "$OPENCODE2_MOCK_PID" 2>/dev/null || true
    wait "$OPENCODE2_MOCK_PID" 2>/dev/null || true
    OPENCODE2_MOCK_PID=""
  fi

  if [[ -n "$OPENCODE2_TMP" ]]; then
    rm -rf "$OPENCODE2_TMP"
    OPENCODE2_TMP=""
  fi
}

# One 2.x turn in its own private server, so no background service outlives
# it and no earlier plugin load answers for this one. Returns the CLI status.
opencode2_run() {
  local directory="$1" prompt="$2" name="$3" status=0

  : >"${OPENCODE2_TMP}/requests.jsonl"

  (cd "$directory" && SANDBOX_MODEL_KEY=sandbox timeout "$CLI_TIMEOUT" \
    opencode2 run --standalone --print-logs --log-level info --model "$OPENCODE2_MODEL" --format json "$prompt" \
    </dev/null >"${OPENCODE2_TMP}/${name}.out" 2>"${OPENCODE2_TMP}/${name}.err") || status=$?

  cp "${OPENCODE2_TMP}/requests.jsonl" "${OPENCODE2_TMP}/${name}.requests.jsonl"

  return "$status"
}

# The number of agent turns whose newest user message carries the marker, split
# by whether any system message names reply-rules.md: "<with> <without>". A
# request offering no tools is 2.x generating the session title from the
# prompt, a harness call rather than a turn of the session's agent, so it is
# left out.
opencode2_reply_rules_split() {
  local name="$1" marker="$2"

  jq -rs --arg marker "$marker" '
    map(.body // {} | select((.tools // []) | length > 0)
      | select((.messages // []) | map(select(.role == "user")) | last | .content | tostring | contains($marker)))
    | map([.messages[] | select(.role == "system") | .content | tostring | contains("reply-rules.md")] | any)
    | "\(map(select(.)) | length) \(map(select(. | not)) | length)"
  ' "${OPENCODE2_TMP}/${name}.requests.jsonl"
}

# The status and the error or output of the first call to a tool, one line.
opencode2_tool_result() {
  local name="$1" tool="$2"

  jq -r --arg tool "$tool" '
    select(.type == "tool_use" and .part.tool == $tool) | .part.state
    | "\(.status) \((.error // .output // "") | tostring | gsub("\n"; " "))"
  ' "${OPENCODE2_TMP}/${name}.out" 2>/dev/null | head -n 1
}

# Asserts what OpenCode 2.x does in a directory whose configuration names the
# plugin at plugin_dir, then that 1.x still starts in v1_dir, a directory 1.x
# reads cleanly. The directory must carry the provider block and no MCP block,
# and the caller runs this before any MCP fixture lands in the user config.
verify_opencode2() {
  local directory="$1" plugin_dir="$2" v1_dir="$3"
  local version="" status=0 target="sandbox-v2-write-probe.txt" result="" split="" guarded=0

  if ! command -v opencode2 >/dev/null 2>&1; then
    fail "OpenCode 2.x is installed as opencode2 (not on PATH)"
    return
  fi

  version="$(timeout "$CLI_TIMEOUT" opencode2 --version </dev/null 2>&1 | head -n 1)" || true

  if [[ "$version" =~ (^|[^0-9])2\.[0-9]+\.[0-9]+ ]]; then
    pass "OpenCode 2.x is installed as opencode2 (${version})"
  else
    fail "OpenCode 2.x is installed as opencode2 (it reported '$(one_line "$version")')"
  fi

  if ! opencode2_begin; then
    fail "the mock model answers on port ${OPENCODE2_MOCK_PORT} ($(one_line "$(cat "${OPENCODE2_TMP}/mock.log" 2>/dev/null)"))"
    return
  fi

  guarded="$(wc -l <"$OPENCODE2_GUARD_LOG" 2>/dev/null || echo 0)"

  opencode2_run "$directory" "SANDBOX-WRITE-PROBE ${target}" write || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "a 2.x turn runs against the mock model (opencode2 exited ${status}: $(one_line "$(tail -n 5 "${OPENCODE2_TMP}/write.err")"))"
  else
    pass "a 2.x turn runs against the mock model"
  fi

  if grep -F 'msg="loading plugin"' "${OPENCODE2_TMP}/write.err" | grep -qF "entrypoint=file://${plugin_dir}/index.js"; then
    pass "2.x loads the plugin from its directory entry, ${plugin_dir}/index.js"
  else
    fail "2.x loads the plugin from its directory entry (no 'loading plugin' line names ${plugin_dir}/index.js)"
  fi

  if grep -qF "$OPENCODE2_PLUGIN_WARN" "${OPENCODE2_TMP}/write.err"; then
    fail "2.x logs no '${OPENCODE2_PLUGIN_WARN}' warning ($(one_line "$(grep -m1 -F "$OPENCODE2_PLUGIN_WARN" "${OPENCODE2_TMP}/write.err")"))"
  else
    pass "2.x logs no '${OPENCODE2_PLUGIN_WARN}' warning"
  fi

  result="$(opencode2_tool_result write write)"

  if [[ "$result" == error*"$OPENCODE2_GATE_TEXT"* && ! -e "${directory}/${target}" ]]; then
    pass "the gate blocks a main-thread write on 2.x, and the file was never created"
  else
    fail "the gate blocks a main-thread write on 2.x (write tool answered '$(one_line "${result:-nothing}")', file present: $([[ -e "${directory}/${target}" ]] && echo yes || echo no))"
  fi

  split="$(opencode2_reply_rules_split write "SANDBOX-WRITE-PROBE")"

  if [[ "${split% *}" -gt 0 && "${split#* }" -eq 0 ]]; then
    pass "2.x hands the main session the reply rules (${split% *} of ${split% *} requests)"
  else
    fail "2.x hands the main session the reply rules (with, without: ${split})"
  fi

  status=0
  opencode2_run "$directory" "SANDBOX-TASK-PROBE ${OPENCODE2_SUBAGENT}" subagent || status=$?
  result="$(opencode2_tool_result subagent subagent)"

  if [[ "$status" -eq 0 && "$result" == completed* ]]; then
    pass "2.x runs subagent ${OPENCODE2_SUBAGENT} on the mock model"
  else
    fail "2.x runs subagent ${OPENCODE2_SUBAGENT} on the mock model (exit ${status}, subagent tool answered '$(one_line "${result:-nothing}")')"
  fi

  split="$(opencode2_reply_rules_split subagent "SANDBOX-CHILD-PROBE")"

  if [[ "${split#* }" -gt 0 && "${split% *}" -eq 0 ]]; then
    pass "a 2.x subagent session gets no reply rules (0 of ${split#* } requests)"
  else
    fail "a 2.x subagent session gets no reply rules (with, without: ${split})"
  fi

  if [[ -f "$OPENCODE2_DATABASE" ]]; then
    pass "2.x keeps its database in its own data directory, ${OPENCODE2_DATABASE}"
  else
    fail "2.x keeps its database in its own data directory (nothing at ${OPENCODE2_DATABASE})"
  fi

  status=0
  (cd "$v1_dir" && timeout "$CLI_TIMEOUT" opencode agent list </dev/null >"${OPENCODE2_TMP}/v1.out" 2>&1) || status=$?

  if [[ "$status" -eq 0 ]] && ! grep -qF "$OPENCODE2_V1_REFUSAL" "${OPENCODE2_TMP}/v1.out"; then
    pass "OpenCode 1.x still starts after 2.x ran"
  else
    fail "OpenCode 1.x still starts after 2.x ran (exit ${status}: $(one_line "$(tail -n 3 "${OPENCODE2_TMP}/v1.out")"))"
  fi

  if [[ "$(wc -l <"$OPENCODE2_GUARD_LOG" 2>/dev/null || echo 0)" -eq "$guarded" ]]; then
    pass "the 2.x turns tried to start no MCP server"
  else
    fail "the 2.x turns tried to start no MCP server ($(one_line "$(tail -n +"$((guarded + 1))" "$OPENCODE2_GUARD_LOG")"))"
  fi

  opencode2_end
}

# OpenCode 1.x and Kilo Code turns against the same mock. The provider travels
# in the runtime's inline configuration variable, the way live/opencode-family.sh
# passes it, and each turn keeps its session database in the temporary
# directory, so nothing outlives the check.
readonly V1_MODEL="sandbox/sandbox-model"
readonly V1_SUBAGENT="docs-architect"
readonly V1_NO_SKILLS_AGENT="sandbox-no-skills-turn-probe"
readonly V1_REPLY_REFUSAL="Formatting violation in your last reply"
readonly V1_RULE_B_TEXT="declares no skills"

# The inline configuration, with the JSON object in $1 merged on top when given.
v1_config() {
  jq -cn --arg url "http://127.0.0.1:${OPENCODE2_MOCK_PORT}/v1" --arg model "$V1_MODEL" \
    --argjson extra "${1:-null}" '{
    provider: {sandbox: {
      npm: "@ai-sdk/openai-compatible",
      name: "Sandbox",
      options: {baseURL: $url, apiKey: "sandbox"},
      models: {"sandbox-model": {name: "Sandbox model", tool_call: true}}
    }},
    model: $model,
    autoupdate: false,
    share: "disabled"
  } + ($extra // {})'
}

# One 1.x or Kilo Code turn, with optional extra configuration in $6. Returns
# the CLI status.
v1_run() {
  local bin="$1" variable="$2" directory="$3" prompt="$4" name="$5" extra="${6:-null}" status=0

  : >"${OPENCODE2_TMP}/requests.jsonl"

  (cd "$directory" && env "${variable}=$(v1_config "$extra")" \
    XDG_DATA_HOME="${OPENCODE2_TMP}/v1-data" XDG_STATE_HOME="${OPENCODE2_TMP}/v1-state" \
    timeout "$CLI_TIMEOUT" "$bin" run --model "$V1_MODEL" --format json "$prompt" \
    </dev/null >"${OPENCODE2_TMP}/${name}.out" 2>"${OPENCODE2_TMP}/${name}.err") || status=$?

  cp "${OPENCODE2_TMP}/requests.jsonl" "${OPENCODE2_TMP}/${name}.requests.jsonl"

  return "$status"
}

# Four counts over the requests of the sessions whose user messages carry the
# marker, one line: "<stored prose> <stored prose still holding an em dash>
# <tool results carrying the needle> <most tool results in one request>".
# Each request repeats the session history, so only zero or not zero matters
# for the first three.
v1_session_facts() {
  local name="$1" marker="$2" prose="$3" needle="$4"

  jq -rs --arg marker "$marker" --arg prose "$prose" --arg needle "$needle" '
    [.[] | .body // {} | select((.messages // []) | map(select(.role == "user") | .content | tostring) | any(contains($marker)))] as $requests
    | [$requests[] | .messages[]] as $all
    | [($all | map(select(.role == "assistant") | .content | tostring | select(contains($prose)))) as $stored
       | ($stored | length), ($stored | map(select(contains("—"))) | length),
       ($all | map(select(.role == "tool") | .content | tostring | select(contains($needle))) | length),
       ($requests | map([.messages[] | select(.role == "tool")] | length) | max // 0)]
    | map(tostring) | join(" ")
  ' "${OPENCODE2_TMP}/${name}.requests.jsonl"
}

# Asserts on one runtime that reply style is a main-thread matter while the
# gate still covers every session: the main session's prose is rewritten and its
# next tool call refused, a docs-architect subagent's prose is left alone and its
# tool calls run, the gate refuses a main-thread write, and rule B still refuses
# a subagent that declares no skills. The directory must carry no MCP block.
verify_reply_style_v1() {
  local label="$1" bin="$2" variable="$3" directory="$4"
  local status=0 target="sandbox-v1-write-probe.txt" stored=0 dashed=0 refused=0 calls=0

  if ! command -v "$bin" >/dev/null 2>&1; then
    fail "${label} is installed as ${bin} (not on PATH)"
    return
  fi

  v1_run "$bin" "$variable" "$directory" "SANDBOX-TEXT-PROBE" text || status=$?
  # Both verify scripts set IFS to newline and tab, so the read names its own separator.
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts text SANDBOX-TEXT-PROBE SANDBOX-MAIN-PROSE "$V1_REPLY_REFUSAL")"

  if [[ "$status" -eq 0 && "$stored" -gt 0 && "$dashed" -eq 0 ]]; then
    pass "${label} rewrites the main session's finished text"
  else
    fail "${label} rewrites the main session's finished text (exit ${status}, stored ${stored}, still dashed ${dashed}: $(one_line "$(tail -n 3 "${OPENCODE2_TMP}/text.err")"))"
  fi

  if [[ "$refused" -gt 0 ]]; then
    pass "${label} refuses the main session's next tool call after prose the reply checks reject"
  else
    fail "${label} refuses the main session's next tool call after prose the reply checks reject (no tool result carries '${V1_REPLY_REFUSAL}', ${calls} tool results)"
  fi

  status=0
  v1_run "$bin" "$variable" "$directory" "SANDBOX-TASK-TEXT-PROBE ${V1_SUBAGENT}" task || status=$?
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts task SANDBOX-CHILD-TEXT-PROBE SANDBOX-CHILD-PROSE "$V1_REPLY_REFUSAL")"

  if [[ "$status" -eq 0 && "$stored" -gt 0 && "$dashed" -gt 0 ]]; then
    pass "${label} leaves a ${V1_SUBAGENT} subagent's finished text as written"
  else
    fail "${label} leaves a ${V1_SUBAGENT} subagent's finished text as written (exit ${status}, stored ${stored}, still dashed ${dashed})"
  fi

  if [[ "$calls" -ge 2 && "$refused" -eq 0 ]]; then
    pass "${label} runs both of the subagent's tool calls, with no reply check refusing either"
  else
    fail "${label} runs both of the subagent's tool calls, with no reply check refusing either (${refused} refused, ${calls} tool results)"
  fi

  status=0
  v1_run "$bin" "$variable" "$directory" "SANDBOX-WRITE-PROBE ${target}" write || status=$?
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts write SANDBOX-WRITE-PROBE SANDBOX-NOTHING "$OPENCODE2_GATE_TEXT")"

  if [[ "$refused" -gt 0 && ! -e "${directory}/${target}" ]]; then
    pass "${label} gate blocks a main-thread write, and the file was never created"
  else
    fail "${label} gate blocks a main-thread write (exit ${status}, ${refused} refusals, file present: $([[ -e "${directory}/${target}" ]] && echo yes || echo no))"
  fi

  cat >"${directory}/.agents/agents/${V1_NO_SKILLS_AGENT}.md" <<'AGENT'
---
description: Fixture subagent that deliberately declares no skills.
mode: subagent
---

Fixture used by the container sandbox to exercise rule B of the preflight gate in a real turn.
AGENT

  status=0
  v1_run "$bin" "$variable" "$directory" "SANDBOX-TASK-TEXT-PROBE ${V1_NO_SKILLS_AGENT}" rule-b || status=$?
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts rule-b SANDBOX-CHILD-TEXT-PROBE SANDBOX-CHILD-PROSE "$V1_RULE_B_TEXT")"
  rm -f "${directory}/.agents/agents/${V1_NO_SKILLS_AGENT}.md"

  if [[ "$refused" -gt 0 ]]; then
    pass "${label} gate still applies rule B inside a subagent session"
  else
    fail "${label} gate still applies rule B inside a subagent session (exit ${status}, no tool result carries '${V1_RULE_B_TEXT}', ${calls} tool results)"
  fi
}

# Asserts on one runtime that a start folder outside any git repository is the
# project, the way Claude Code, Codex and OpenCode 2.x treat it: the gate
# refuses a main-thread write inside the folder, and does not refuse one to a
# folder beside it. The runtime hands the plugin "/" as its worktree there, so
# a plugin that anchored on the worktree protected the whole disk instead. The
# outside write runs with external_directory allowed, so only the gate decides.
# The directory must carry no MCP block and no .git above it.
verify_start_folder_v1() {
  local label="$1" bin="$2" variable="$3" directory="$4"
  local status=0 inside="sandbox-v1-start-folder-probe.txt" outside="" stored=0 dashed=0 refused=0 calls=0

  if ! command -v "$bin" >/dev/null 2>&1; then
    fail "${label} is installed as ${bin} (not on PATH)"
    return
  fi

  if git -C "$directory" rev-parse --git-dir >/dev/null 2>&1; then
    fail "${label} start folder ${directory} is outside any git repository (git found one)"
    return
  fi

  v1_run "$bin" "$variable" "$directory" "SANDBOX-WRITE-PROBE ${inside}" start-inside || status=$?
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts start-inside SANDBOX-WRITE-PROBE SANDBOX-NOTHING "$OPENCODE2_GATE_TEXT")"

  if [[ "$refused" -gt 0 && ! -e "${directory}/${inside}" ]]; then
    pass "${label} gate treats a non-git start folder as the project and blocks a main-thread write inside it"
  else
    fail "${label} gate treats a non-git start folder as the project and blocks a main-thread write inside it (exit ${status}, ${refused} refusals, file present: $([[ -e "${directory}/${inside}" ]] && echo yes || echo no))"
  fi

  outside="$(mktemp -d -t sandbox-v1-outside-XXXXXXXX)"
  status=0
  v1_run "$bin" "$variable" "$directory" "SANDBOX-WRITE-PROBE ${outside}/probe.txt" start-outside \
    '{"permission": {"external_directory": "allow"}}' || status=$?
  IFS=' ' read -r stored dashed refused calls <<<"$(v1_session_facts start-outside SANDBOX-WRITE-PROBE SANDBOX-NOTHING "$OPENCODE2_GATE_TEXT")"

  if [[ "$calls" -gt 0 && "$refused" -eq 0 && -e "${outside}/probe.txt" ]]; then
    pass "${label} gate leaves a main-thread write outside the non-git start folder alone, and the file was created"
  else
    fail "${label} gate leaves a main-thread write outside the non-git start folder alone (exit ${status}, ${refused} refusals, ${calls} tool results, file present: $([[ -e "${outside}/probe.txt" ]] && echo yes || echo no))"
  fi

  rm -rf "$outside"
}

# Notes how many MCP launches the guard refused during the whole run.
note_mcp_guard() {
  local refused=0

  refused="$(wc -l <"$OPENCODE2_GUARD_LOG" 2>/dev/null || echo 0)"
  note "the MCP launcher guard refused ${refused} docker, npx or uvx calls, so no real MCP server started"
}
