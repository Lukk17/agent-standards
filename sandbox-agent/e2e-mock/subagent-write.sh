#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: subagent-write.sh
# Description: Proves, for every supported agent, that a real subagent writes
#              a real file. Each pinned agent binary runs in a copy of the
#              imported project, hooks, gate and generated subagents included,
#              against server.mjs, a free local model that replays a scripted
#              conversation: the main thread starts python-pro, python-pro
#              writes e2e-subagent-proof.txt, and both turns end. A second
#              scripted case has the main thread write a file itself, which the
#              gate has to deny. On Claude Code a third case starts the
#              code-reviewer subagent headless and checks that it preloaded the
#              project's application-security-review skill, not the built-in
#              /security-review command. On Codex a fourth case starts
#              backend-architect, whose tools leave out bash, and checks that
#              its turns offer no shell tool, against the python-pro turns of
#              the first case, which do. Only the model is mocked.
# Usage: sourced by verify-project.sh, which defines pass, fail, note and
#        one_line, sources lib-opencode2.sh first, calls
#        verify_subagent_write <project> and calls e2e_end from its EXIT trap.
#        Or run directly against an imported project:
#          subagent-write.sh <project> [claude-code|codex|copilot|opencode2|opencode|kilo-code ...]
# Environment:
#   SANDBOX_MOCK_PORT    Port the mock listens on, shared with lib-opencode2.sh,
#                        whose sections end before this one starts. Default
#                        49611.
#   SANDBOX_E2E_TIMEOUT  Seconds allowed per agent run. Default 120.
#   SANDBOX_E2E_KEEP     Set to 1 to keep the work directory for inspection.
# Exit codes (direct run only):
#   0  Nothing failed. A KNOWN-GAP line does not fail the run.
#   1  At least one check failed.
#   2  Misuse.
# -----------------------------------------------------------------------------

E2E_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly E2E_DIR
readonly E2E_SERVER="${E2E_DIR}/server.mjs"
readonly E2E_RECORDS="${E2E_DIR}/records.py"
readonly E2E_TIMEOUT="${SANDBOX_E2E_TIMEOUT:-120}"
readonly E2E_MODEL="sandbox-model"
readonly E2E_SUBAGENT="python-pro"
readonly E2E_PROOF="e2e-subagent-proof.txt"
readonly E2E_CONTENT="written-by-the-python-pro-subagent"
readonly E2E_MAIN_PROOF="e2e-main-thread-proof.txt"
readonly E2E_MAIN_CONTENT="written-by-the-main-thread"
readonly E2E_AGENTS=(claude-code codex copilot opencode2 opencode kilo-code)
# Every tool name a supported agent writes a file with, as records.py counts
# them, and every tool name one starts a subagent with, as server.mjs offers.
readonly E2E_WRITE_TOOLS='["Write","Edit","MultiEdit","Bash","create","edit","write","apply_patch","exec_command","shell","bash"]'
readonly E2E_SPAWN_TOOLS='["Agent","Task","task","subagent","spawn_agent"]'
# The Claude Code review case: the subagent started, the skill its definition
# preloads, and the opening of the prompt of Claude Code's own built-in
# /security-review command, read from the pinned 2.1.314 binary, which the
# check confirms is still in the binary it runs.
readonly E2E_REVIEWER="code-reviewer"
readonly E2E_REVIEW_SKILL="application-security-review"
readonly E2E_REVIEW_FILE="e2e-review-target.txt"
readonly E2E_REVIEW_TOKEN="e2e-review"
readonly E2E_BUILTIN_REVIEW_MARKER="You are a senior security engineer conducting a focused security review of the changes on this branch."
# The Codex no-shell case: an agent whose canonical tools leave out bash, so
# its generated file sets features.shell_tool = false, and every tool name a
# Codex build has offered a shell under.
readonly E2E_NO_SHELL_AGENT="backend-architect"
readonly E2E_SHELL_TOOLS='["exec_command","write_stdin","shell","shell_command","local_shell"]'

E2E_TMP=""
E2E_PID=""
E2E_PORT=""
E2E_LABEL=""
E2E_BIN=""
# The texts the checks look for, read from the imported project itself by
# e2e_read_needles: the subagent opening, each main-thread reminder (Claude
# Code's first, then the one every other agent injects), the first line of
# python-pro's definition, the gate's main-thread write refusal, and the first
# prose line of the project's application-security-review skill.
E2E_SUBAGENT_TEXT=""
E2E_MAIN_TEXTS="[]"
E2E_DEFINITION=""
E2E_GATE_TEXT=""
E2E_SKILL_LINE=""

e2e_known_gap() { printf 'KNOWN-GAP  %s\n' "$*"; }

# Starts the mock and waits until it accepts a connection.
e2e_begin() {
  local attempt=0

  E2E_PORT="${OPENCODE2_MOCK_PORT:-${SANDBOX_MOCK_PORT:-49611}}"
  E2E_TMP="$(mktemp -d -t sandbox-e2e-XXXXXXXX)"
  : >"${E2E_TMP}/requests.jsonl"

  node "$E2E_SERVER" "$E2E_PORT" "${E2E_TMP}/requests.jsonl" >"${E2E_TMP}/server.log" 2>&1 &
  E2E_PID=$!

  while [[ "$attempt" -lt 50 ]]; do
    if (exec 3<>"/dev/tcp/127.0.0.1/${E2E_PORT}") 2>/dev/null; then
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 0.1
  done

  return 1
}

e2e_end() {
  if [[ -n "$E2E_PID" ]]; then
    kill "$E2E_PID" 2>/dev/null || true
    wait "$E2E_PID" 2>/dev/null || true
    E2E_PID=""
  fi

  if [[ -n "$E2E_TMP" && "${SANDBOX_E2E_KEEP:-0}" != "1" ]]; then
    rm -rf "$E2E_TMP"
  elif [[ -n "$E2E_TMP" ]]; then
    note "kept the subagent-write work directory at ${E2E_TMP}"
  fi

  E2E_TMP=""
}

# Reads the texts the checks need from the imported project, so a change of
# wording upstream moves the check with it. Parsed with ast, never executed.
e2e_read_needles() {
  local project="$1" needles=""

  needles="$(python3 -I -S - "$project" "$E2E_REVIEW_SKILL" <<'PY'
import ast
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def constants(path):
    found = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.value
    return found


def first_sentence(text):
    return text.split(". ")[0]


reminder = constants(root / ".agents/hooks/copilot/prompt-reminder/prompt_reminder.py")
gate = constants(root / ".agents/hooks/preflight-gate/preflight_gate.py")
claude = constants(root / ".agents/hooks/claude/preflight-reminder/preflight_reminder.py")["REMINDER"]


def body(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[lines.index("---", 1) + 1:]


skill = root / ".agents/skills" / sys.argv[2] / "SKILL.md"

print(json.dumps({
    "subagent": reminder["SUBAGENT_OPENING"],
    "main": [first_sentence(claude), first_sentence(reminder["REMINDER"])],
    "definition": next(line for line in body(root / ".claude/agents/python-pro/python-pro.md") if line.strip()),
    "gate": first_sentence(gate["RULE_A_REASON"]),
    "skill": next(line for line in body(skill) if line.strip() and not line.startswith("#")),
}))
PY
  )" || return 1

  E2E_SUBAGENT_TEXT="$(jq -r '.subagent' <<<"$needles")"
  E2E_MAIN_TEXTS="$(jq -c '.main' <<<"$needles")"
  E2E_DEFINITION="$(jq -r '.definition' <<<"$needles")"
  E2E_GATE_TEXT="$(jq -r '.gate' <<<"$needles")"
  E2E_SKILL_LINE="$(jq -r '.skill' <<<"$needles")"
}

# The main-thread reminder this agent injects: Claude Code's own, or the one
# Codex, Copilot and the OpenCode plugin share.
e2e_own_main_text() {
  if [[ "$1" == "claude-code" ]]; then
    jq -r '.[0]' <<<"$E2E_MAIN_TEXTS"
  else
    jq -r '.[1]' <<<"$E2E_MAIN_TEXTS"
  fi
}

# The agent's label and binary, set into E2E_LABEL and E2E_BIN.
e2e_identify() {
  case "$1" in
    claude-code) E2E_LABEL="Claude Code"; E2E_BIN="claude" ;;
    codex) E2E_LABEL="Codex"; E2E_BIN="codex" ;;
    copilot) E2E_LABEL="GitHub Copilot CLI"; E2E_BIN="copilot" ;;
    opencode2) E2E_LABEL="OpenCode 2.x"; E2E_BIN="opencode2" ;;
    opencode) E2E_LABEL="OpenCode 1.x"; E2E_BIN="opencode" ;;
    kilo-code) E2E_LABEL="Kilo Code"; E2E_BIN="kilocode" ;;
    *) return 1 ;;
  esac
}

# A fresh copy of the imported project for one agent, with what that agent
# needs to reach the mock: Claude Code, Codex and Copilot keep the project as
# imported and switch MCP servers off on the command line, while the OpenCode
# family drops the MCP block, as every other sandbox turn does, and 1.x copies
# its .v1 backstop in the way docs/AGENT_TOOLING.md tells a 1.x user to.
e2e_prepare() {
  local agent="$1" project="$2" dir="$3"

  mkdir -p "${dir}/project" "${dir}/state/exports"
  cp -a "${project}/." "${dir}/project/"

  case "$agent" in
    claude-code)
      printf '{"mcpServers": {}}\n' >"${dir}/state/no-mcp.json"
      ;;
    codex)
      mkdir -p "${dir}/state/codex-home"
      cat >"${dir}/state/codex-home/config.toml" <<EOF
model = "${E2E_MODEL}"
model_provider = "sandbox"

[model_providers.sandbox]
name = "Sandbox"
base_url = "http://127.0.0.1:${E2E_PORT}/v1"
env_key = "SANDBOX_MODEL_KEY"
wire_api = "responses"

[projects."${dir}/project"]
trust_level = "trusted"
EOF
      ;;
    copilot)
      mkdir -p "${dir}/state/copilot-home"
      jq -n --arg p "${dir}/project" '{trustedFolders: [$p]}' >"${dir}/state/copilot-home/config.json"
      ;;
    opencode2)
      rm -f "${dir}/project/.mcp.json"
      jq --argjson providers "$(opencode2_providers)" 'del(.mcp) | .providers = $providers' \
        "${project}/opencode.json" >"${dir}/project/opencode.json"
      ;;
    opencode | kilo-code)
      rm -f "${dir}/project/.mcp.json"
      jq 'del(.mcp)' "${project}/opencode.json" >"${dir}/project/opencode.json"
      if [[ "$agent" == "opencode" ]]; then
        opencode_use_v1_backstop "${dir}/project"
      fi
      ;;
  esac
}

# Prints one -c override per Codex MCP server, switching each one off.
e2e_codex_mcp_off() {
  python3 -I -S -c 'import sys, tomllib
for name in sorted(tomllib.load(open(sys.argv[1], "rb")).get("mcp_servers", {})):
    print("-c")
    print(f"mcp_servers.{name}.enabled=false")' "$1"
}

# Prints one --disable-mcp-server pair per server Copilot reads.
e2e_copilot_mcp_off() {
  jq -r '.mcpServers // {} | keys[]' "${1}/.mcp.json" "${1}/.github/mcp.json" 2>/dev/null | sort -u |
    while IFS= read -r name; do
      printf -- '--disable-mcp-server\n%s\n' "$name"
    done
}

# Runs one scripted case through one agent binary in its project copy. The
# request log is cut per case. Returns the CLI status.
e2e_invoke() {
  local agent="$1" dir="$2" prompt="$3" name="$4" status=0 id=""
  local project="${dir}/project" state="${dir}/state" url="http://127.0.0.1:${E2E_PORT}"
  local -a off=()

  : >"${E2E_TMP}/requests.jsonl"

  case "$agent" in
    claude-code)
      (cd "$project" && env -u ANTHROPIC_API_KEY \
        CLAUDE_CONFIG_DIR="${state}/claude-config" ANTHROPIC_BASE_URL="$url" ANTHROPIC_AUTH_TOKEN=sandbox \
        ANTHROPIC_MODEL="$E2E_MODEL" ANTHROPIC_SMALL_FAST_MODEL="$E2E_MODEL" \
        ANTHROPIC_DEFAULT_HAIKU_MODEL="$E2E_MODEL" ANTHROPIC_DEFAULT_SONNET_MODEL="$E2E_MODEL" \
        ANTHROPIC_DEFAULT_OPUS_MODEL="$E2E_MODEL" CLAUDE_CODE_SUBAGENT_MODEL="$E2E_MODEL" \
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 \
        timeout "$E2E_TIMEOUT" claude -p "$prompt" --output-format stream-json --verbose \
        --permission-mode acceptEdits --max-turns 6 --model "$E2E_MODEL" \
        --strict-mcp-config --mcp-config "${state}/no-mcp.json" \
        </dev/null >"${dir}/${name}.out" 2>"${dir}/${name}.err") || status=$?
      ;;
    codex)
      mapfile -t off < <(e2e_codex_mcp_off "${project}/.codex/config.toml")
      (cd "$project" && CODEX_HOME="${state}/codex-home" SANDBOX_MODEL_KEY=sandbox \
        timeout "$E2E_TIMEOUT" codex exec --json "${off[@]}" \
        --dangerously-bypass-approvals-and-sandbox --dangerously-bypass-hook-trust --cd "$project" "$prompt" \
        </dev/null >"${dir}/${name}.out" 2>"${dir}/${name}.err") || status=$?
      ;;
    copilot)
      mapfile -t off < <(e2e_copilot_mcp_off "$project")
      (cd "$project" && COPILOT_HOME="${state}/copilot-home" COPILOT_OFFLINE=true COPILOT_AUTO_UPDATE=false \
        COPILOT_PROVIDER_TYPE=openai COPILOT_PROVIDER_WIRE_API=responses COPILOT_PROVIDER_BASE_URL="${url}/v1" \
        COPILOT_PROVIDER_API_KEY=sandbox COPILOT_PROVIDER_MAX_PROMPT_TOKENS=128000 \
        COPILOT_PROVIDER_MAX_OUTPUT_TOKENS=8192 COPILOT_MODEL="$E2E_MODEL" COPILOT_ALLOW_ALL=true \
        GITHUB_COPILOT_PROMPT_MODE_REPO_HOOKS=true \
        timeout "$E2E_TIMEOUT" copilot -p "$prompt" --output-format json --allow-all --no-ask-user \
        --log-dir "${state}/logs" --disable-builtin-mcps "${off[@]}" \
        </dev/null >"${dir}/${name}.out" 2>"${dir}/${name}.err") || status=$?
      ;;
    opencode2)
      (cd "$project" && OPENCODE2_DATA_HOME="${state}/data" SANDBOX_MODEL_KEY=sandbox \
        timeout "$E2E_TIMEOUT" opencode2 run --standalone --model "$OPENCODE2_MODEL" --format json "$prompt" \
        </dev/null >"${dir}/${name}.out" 2>"${dir}/${name}.err") || status=$?
      ;;
    opencode | kilo-code)
      local variable="OPENCODE_CONFIG_CONTENT" config=""
      [[ "$agent" == "kilo-code" ]] && variable="KILO_CONFIG_CONTENT"
      # The small model names the mock too, so the title request stays local
      # rather than going to the runtime's own cloud model.
      config="$(v1_config "{\"small_model\": \"${V1_MODEL}\"}")"
      # Each case keeps its own data directory. Measured on Kilo Code 7.5.5: a
      # run in a data directory where `export` had read a child session hung
      # before its first model request in 2 of 4 tries.
      (cd "$project" && env "${variable}=${config}" XDG_DATA_HOME="${state}/data-${name}" XDG_STATE_HOME="${state}/xdg-state-${name}" \
        timeout "$E2E_TIMEOUT" "$E2E_BIN" run --model "$V1_MODEL" --format json "$prompt" \
        </dev/null >"${dir}/${name}.out" 2>"${dir}/${name}.err") || status=$?

      # The run streams the main session only, so every session the mock saw
      # is exported, and records.py tells a child by its parentID.
      while IFS= read -r id; do
        [[ "$id" =~ ^[A-Za-z0-9_]+$ ]] || continue
        (cd "$project" && env "${variable}=${config}" XDG_DATA_HOME="${state}/data-${name}" XDG_STATE_HOME="${state}/xdg-state-${name}" \
          timeout "$E2E_TIMEOUT" "$E2E_BIN" export "$id" \
          </dev/null >"${state}/exports/${name}-${id}.json" 2>>"${dir}/${name}.err") || true
      done < <(jq -r '.headers["x-session-id"] // empty' "${E2E_TMP}/requests.jsonl" | sort -u)
      ;;
  esac

  cp "${E2E_TMP}/requests.jsonl" "${dir}/${name}.requests.jsonl"

  return "$status"
}

# Facts over one case's request log, one line: "<spawns answered> <subagent
# writes answered> <main-thread writes> <role conflicts> <subagent turns>
# <subagent turns with the subagent text> <subagent turns with a main-thread
# reminder> <subagent turns with python-pro's definition> <main-thread turns>
# <main-thread turns with this agent's own reminder> <gate refusals of a
# main-thread write>". A turn is a request the marker and the headers both
# place in the same session and that offers tools. Each request repeats its
# session's history, so only zero or not zero matters for the counts of calls.
# An unreadable log counts as all zeros, so every check that needs a fact fails
# rather than passing on a parse error.
e2e_facts() {
  local log="$1" path="$2" own="$3" facts=""

  facts="$(jq -rs --arg path "$path" --argjson writes "$E2E_WRITE_TOOLS" --argjson spawns "$E2E_SPAWN_TOOLS" \
    --arg sub "$E2E_SUBAGENT_TEXT" --argjson mains "$E2E_MAIN_TEXTS" --arg def "$E2E_DEFINITION" \
    --arg own "$own" --arg gate "$E2E_GATE_TEXT" '
    def wrote: .calls[] | select((.name as $n | $writes | index($n)) and (.args | tojson | contains($path)));
    map(select(.role == "subagent" and .header_role == "subagent" and .tool_count > 0)) as $turns
    | map(select(.role == "main" and .header_role == "main" and .tool_count > 0)) as $mainturns
    | [ (map(select(.role == "main") | [.calls[] | select((.name as $n | $spawns | index($n)) and .result != null)] | length) | add // 0),
        ($turns | map([wrote | select(.result != null)] | length) | add // 0),
        (map(select(.role == "main") | [wrote] | length) | add // 0),
        (map(select((.reply.text // "") | startswith("E2E: role conflict"))) | length),
        ($turns | length),
        ($turns | map(select(.context | contains($sub))) | length),
        ($turns | map(select(.context as $c | any($mains[]; . as $m | $c | contains($m)))) | length),
        ($turns | map(select(.system | contains($def))) | length),
        ($mainturns | length),
        ($mainturns | map(select(.context | contains($own))) | length),
        (map(select(.role == "main") | [wrote | select((.result // "") | contains($gate))] | length) | add // 0)
      ] | map(tostring) | join(" ")' "$log" 2>/dev/null)" || facts="0 0 0 0 0 0 0 0 0 0 0"
  printf '%s\n' "$facts"
}

# Facts over the review case's request log, one line: "<subagent turns>
# <subagent turns with the skill line> <subagent turns with the built-in
# command's prompt> <spawns answered>". All zeros when the log is unreadable.
e2e_review_facts() {
  local log="$1" facts=""

  facts="$(jq -rs --arg skill "$E2E_SKILL_LINE" --arg builtin "$E2E_BUILTIN_REVIEW_MARKER" --argjson spawns "$E2E_SPAWN_TOOLS" '
    map(select(.role == "subagent" and .header_role == "subagent" and .tool_count > 0)) as $turns
    | [ ($turns | length),
        ($turns | map(select(.context | contains($skill))) | length),
        ($turns | map(select(.context | contains($builtin))) | length),
        (map(select(.role == "main") | [.calls[] | select((.name as $n | $spawns | index($n)) and .result != null)] | length) | add // 0)
      ] | map(tostring) | join(" ")' "$log" 2>/dev/null)" || facts="0 0 0 0"
  printf '%s\n' "$facts"
}

# Facts over one case's request log, one line: "<subagent turns> <subagent
# turns offering a shell tool> <spawns answered>". All zeros when the log is
# unreadable.
e2e_shell_facts() {
  local log="$1" facts=""

  facts="$(jq -rs --argjson shells "$E2E_SHELL_TOOLS" --argjson spawns "$E2E_SPAWN_TOOLS" '
    map(select(.role == "subagent" and .header_role == "subagent" and .tool_count > 0)) as $turns
    | [ ($turns | length),
        ($turns | map(select(any(.tools[]?; . as $t | $shells | index($t)))) | length),
        (map(select(.role == "main") | [.calls[] | select((.name as $n | $spawns | index($n)) and .result != null)] | length) | add // 0)
      ] | map(tostring) | join(" ")' "$log" 2>/dev/null)" || facts="0 0 0"
  printf '%s\n' "$facts"
}

# Returns 0 when the agent binary on PATH, or the package it was installed
# from, still holds the built-in command's prompt, so its absence from a
# request means something.
e2e_binary_holds() {
  local marker="$1" binary=""

  binary="$(readlink -f "$(command -v "$E2E_BIN")" 2>/dev/null)" || return 1
  [[ -f "$binary" ]] || return 1
  grep -aqF -- "$marker" "$binary" || grep -raqF -- "$marker" "$(dirname "$binary")/.."
}

# Claude Code only: the main thread starts the project's code-reviewer, whose
# definition preloads application-security-review, and the subagent answers at once. Its
# requests must carry the project skill's own line and never the prompt of the
# built-in /security-review command of the same name.
e2e_check_review() {
  local dir="$1" status=0 turns=0 with_skill=0 with_builtin=0 spawns=0

  e2e_invoke claude-code "$dir" \
    "E2E-REVIEW ${E2E_REVIEWER} ${dir}/project/${E2E_REVIEW_FILE} ${E2E_REVIEW_TOKEN}" review || status=$?
  IFS=' ' read -r turns with_skill with_builtin spawns <<<"$(e2e_review_facts "${dir}/review.requests.jsonl")"

  if ! e2e_binary_holds "$E2E_BUILTIN_REVIEW_MARKER"; then
    fail "${E2E_LABEL}: the built-in /security-review prompt is still in the ${E2E_BIN} binary, so its absence below proves something (not found: '${E2E_BUILTIN_REVIEW_MARKER}')"
  fi

  if [[ "$spawns" -gt 0 && "$turns" -gt 0 && "$with_skill" -eq "$turns" && "$with_builtin" -eq 0 ]]; then
    pass "${E2E_LABEL}: ${E2E_REVIEWER} preloads the project's ${E2E_REVIEW_SKILL} skill and not the built-in /${E2E_REVIEW_SKILL} command (${turns} of ${turns} turns)"
  else
    fail "${E2E_LABEL}: ${E2E_REVIEWER} preloads the project's ${E2E_REVIEW_SKILL} skill and not the built-in /${E2E_REVIEW_SKILL} command (exit ${status}, ${spawns} spawn(s) answered, ${turns} subagent turn(s), ${with_skill} with '${E2E_SKILL_LINE}', ${with_builtin} with the built-in prompt)"
  fi
}

# Codex only: the main thread starts an agent whose tools leave out bash, and
# the subagent answers at once. None of its turns may offer a shell tool,
# while python-pro's turns in the spawn case must, so the check can see one.
e2e_check_no_shell() {
  local dir="$1" status=0 turns=0 with_shell=0 spawns=0 control_turns=0 control_shell=0 _spawned=0

  e2e_invoke codex "$dir" \
    "E2E-REVIEW ${E2E_NO_SHELL_AGENT} ${dir}/project/${E2E_REVIEW_FILE} ${E2E_REVIEW_TOKEN}" no-shell || status=$?
  IFS=' ' read -r turns with_shell spawns <<<"$(e2e_shell_facts "${dir}/no-shell.requests.jsonl")"
  IFS=' ' read -r control_turns control_shell _spawned <<<"$(e2e_shell_facts "${dir}/spawn.requests.jsonl")"

  if [[ "$control_shell" -gt 0 && "$spawns" -gt 0 && "$turns" -gt 0 && "$with_shell" -eq 0 ]]; then
    pass "${E2E_LABEL}: ${E2E_NO_SHELL_AGENT}, whose tools leave out bash, is offered no shell (${turns} turns), while ${E2E_SUBAGENT} is (${control_shell} of ${control_turns} turns)"
  else
    fail "${E2E_LABEL}: ${E2E_NO_SHELL_AGENT}, whose tools leave out bash, is offered no shell (exit ${status}, ${spawns} spawn(s) answered, ${with_shell} of ${turns} subagent turn(s) offering a shell, ${control_shell} of ${control_turns} ${E2E_SUBAGENT} turn(s) offering one)"
  fi
}

# The scripted cases and every check, for one agent.
e2e_check_agent() {
  local agent="$1" project="$2"
  local dir="${E2E_TMP}/${agent}" status=0 records="" proof="" denied="" own=""
  local spawns=0 sub_writes=0 main_writes=0 conflicts=0 turns=0 with_sub=0 with_main=0 with_def=0
  local main_turns=0 main_with_own=0 refusals=0 rec_sub=0 rec_main=0

  e2e_identify "$agent"

  if ! command -v "$E2E_BIN" >/dev/null 2>&1; then
    fail "${E2E_LABEL} is installed as ${E2E_BIN} (not on PATH)"
    return
  fi

  e2e_prepare "$agent" "$project" "$dir"
  proof="${dir}/project/${E2E_PROOF}"
  denied="${dir}/project/${E2E_MAIN_PROOF}"
  own="$(e2e_own_main_text "$agent")"

  e2e_invoke "$agent" "$dir" "E2E-SPAWN ${E2E_SUBAGENT} ${proof} ${E2E_CONTENT}" spawn || status=$?
  # Both verify scripts set IFS to newline and tab, so each read names its own separator.
  IFS=' ' read -r spawns sub_writes main_writes conflicts turns with_sub with_main with_def main_turns main_with_own refusals \
    <<<"$(e2e_facts "${dir}/spawn.requests.jsonl" "$proof" "$own")"
  records="$(python3 -I -S "$E2E_RECORDS" "$agent" "${dir}/state" "$proof" 2>&1)" || records="unreadable: ${records}"
  IFS=' ' read -r rec_sub rec_main <<<"$records"

  if [[ -f "$proof" ]] && printf '%s\n' "$E2E_CONTENT" | cmp -s - "$proof"; then
    pass "${E2E_LABEL}: ${E2E_SUBAGENT} wrote ${E2E_PROOF} with the exact content"
  elif [[ -f "$proof" ]]; then
    fail "${E2E_LABEL}: ${E2E_SUBAGENT} wrote ${E2E_PROOF} with the exact content (it holds '$(one_line "$(head -c 200 "$proof")")')"
  else
    fail "${E2E_LABEL}: ${E2E_SUBAGENT} wrote ${E2E_PROOF} with the exact content (no file, exit ${status}, ${spawns} spawn(s) answered, ${turns} subagent turn(s): $(one_line "$(tail -n 3 "${dir}/spawn.err")"))"
  fi

  if [[ "$spawns" -gt 0 && "$sub_writes" -gt 0 && "$main_writes" -eq 0 && "$conflicts" -eq 0 &&
    "$rec_sub" =~ ^[0-9]+$ && "$rec_sub" -gt 0 && "$rec_main" -eq 0 ]]; then
    pass "${E2E_LABEL}: the write was made inside the subagent session (mock: the main thread started it and its own session answered the write call; agent record: ${rec_sub} subagent, 0 main-thread)"
  else
    fail "${E2E_LABEL}: the write was made inside the subagent session (spawns answered ${spawns}, subagent writes answered ${sub_writes}, main-thread writes ${main_writes}, marker and header conflicts ${conflicts}, agent record '${records}')"
  fi

  if [[ "$turns" -gt 0 && "$with_def" -eq "$turns" ]]; then
    pass "${E2E_LABEL}: every subagent turn ran under ${E2E_SUBAGENT}'s own definition (${turns} of ${turns})"
  else
    fail "${E2E_LABEL}: every subagent turn ran under ${E2E_SUBAGENT}'s own definition (${with_def} of ${turns})"
  fi

  if [[ "$main_turns" -gt 0 && "$main_with_own" -eq "$main_turns" ]]; then
    pass "${E2E_LABEL}: every main-thread turn carries the main-thread reminder (${main_turns} of ${main_turns})"
  else
    fail "${E2E_LABEL}: every main-thread turn carries the main-thread reminder (${main_with_own} of ${main_turns} with '${own}')"
  fi

  if [[ "$turns" -gt 0 && "$with_sub" -eq "$turns" && "$with_main" -eq 0 ]]; then
    pass "${E2E_LABEL}: every subagent turn carries the subagent text and none the main-thread reminder (${turns} turns)"
  else
    fail "${E2E_LABEL}: every subagent turn carries the subagent text and none the main-thread reminder (${turns} turns, ${with_sub} with '${E2E_SUBAGENT_TEXT}', ${with_main} with a main-thread reminder)"
  fi

  status=0
  e2e_invoke "$agent" "$dir" "E2E-MAIN-WRITE ${denied} ${E2E_MAIN_CONTENT}" main-write || status=$?
  IFS=' ' read -r spawns sub_writes main_writes conflicts turns with_sub with_main with_def main_turns main_with_own refusals \
    <<<"$(e2e_facts "${dir}/main-write.requests.jsonl" "$denied" "$own")"

  if [[ "$main_writes" -gt 0 && "$refusals" -gt 0 && ! -e "$denied" ]]; then
    pass "${E2E_LABEL}: the gate denies the main thread's own write, and the file was never created"
  elif [[ "$main_writes" -gt 0 && -e "$denied" && "$agent" == "copilot" ]]; then
    e2e_known_gap "${E2E_LABEL}: the main thread's own write landed, as AGENTS.md records: the Copilot preToolUse payload carries no agent identifier, so the gate cannot tell the main thread from a subagent"
  else
    fail "${E2E_LABEL}: the gate denies the main thread's own write (exit ${status}, ${main_writes} main-thread write call(s), ${refusals} carrying '${E2E_GATE_TEXT}', file present: $([[ -e "$denied" ]] && echo yes || echo no))"
  fi

  if [[ "$agent" == "claude-code" ]]; then
    e2e_check_review "$dir"
  fi

  if [[ "$agent" == "codex" ]]; then
    e2e_check_no_shell "$dir"
  fi
}

# Every check for every agent named, all by default. Runs the agents in the
# order of E2E_AGENTS, one at a time against one mock.
verify_subagent_write() {
  local project="$1"
  shift
  local agents=("$@") agent=""

  [[ "${#agents[@]}" -gt 0 ]] || agents=("${E2E_AGENTS[@]}")

  if ! e2e_read_needles "$project"; then
    fail "the subagent-write check reads its texts from the imported project (${project})"
    return
  fi

  if ! e2e_begin; then
    fail "the scripted mock model answers on port ${E2E_PORT} ($(one_line "$(cat "${E2E_TMP}/server.log" 2>/dev/null)"))"
    e2e_end
    return
  fi

  note "each agent runs in its own copy of the imported project against server.mjs on port ${E2E_PORT}; only the model is mocked."

  for agent in "${agents[@]}"; do
    if ! e2e_identify "$agent"; then
      fail "unknown agent '${agent}' for the subagent-write check (expected one of: ${E2E_AGENTS[*]})"
      continue
    fi
    e2e_check_agent "$agent" "$project"
  done

  e2e_end
}

# --- Direct run ---------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
  IFS=$'\n\t'

  if [[ $# -lt 1 || ! -d "$1" ]]; then
    echo "usage: subagent-write.sh <imported project> [agent ...]" >&2
    exit 2
  fi

  E2E_PASSES=0
  E2E_FAILURES=0
  pass() { printf 'PASS  %s\n' "$*"; E2E_PASSES=$((E2E_PASSES + 1)); }
  fail() { printf 'FAIL  %s\n' "$*"; E2E_FAILURES=$((E2E_FAILURES + 1)); }
  note() { printf 'NOTE  %s\n' "$*"; }
  one_line() { printf '%s' "$1" | tail -n 3 | tr '\n' ' ' | tr -s ' '; }
  # shellcheck disable=SC2034  # read by lib-opencode2.sh
  CLI_TIMEOUT="$E2E_TIMEOUT"

  # shellcheck source-path=SCRIPTDIR source=../lib-opencode2.sh
  source "${E2E_DIR}/../lib-opencode2.sh"
  trap e2e_end EXIT

  verify_subagent_write "$(cd "$1" && pwd)" "${@:2}"

  printf 'Passed: %d\nFailed: %d\n' "$E2E_PASSES" "$E2E_FAILURES"
  [[ "$E2E_FAILURES" -eq 0 ]] || exit 1
fi
