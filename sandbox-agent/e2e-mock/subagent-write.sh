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
#              gate has to deny. Only the model is mocked.
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
# The Copilot CLI's own subagent prompt block, AGENTS.md "Maintenance
# follow-ups", and the gap its preToolUse payload leaves, the same switches
# live/copilot.sh carries.
readonly E2E_COPILOT_NO_WRITE_MARKER="CRITICAL: Do NOT write output to files"

E2E_TMP=""
E2E_PID=""
E2E_PORT=""
E2E_LABEL=""
E2E_BIN=""
# The texts the checks look for, read from the imported project itself by
# e2e_read_needles: the subagent opening, each main-thread reminder, the first
# line of python-pro's definition, and the gate's main-thread write refusal.
E2E_SUBAGENT_TEXT=""
E2E_MAIN_TEXTS="[]"
E2E_DEFINITION=""
E2E_GATE_TEXT=""

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

  needles="$(python3 -I -S - "$project" <<'PY'
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


reminder = constants(root / ".agents/hooks/copilot/prompt_reminder.py")
gate = constants(root / ".agents/hooks/preflight_gate.py")
settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
claude = next(
    hook["command"].split("echo '", 1)[1]
    for entry in settings["hooks"]["UserPromptSubmit"]
    for hook in entry["hooks"]
    if "echo '" in hook.get("command", "")
)
lines = (root / ".claude/agents/python-pro.md").read_text(encoding="utf-8").splitlines()
body = lines[lines.index("---", 1) + 1:]

print(json.dumps({
    "subagent": reminder["SUBAGENT_OPENING"],
    "main": [first_sentence(claude), first_sentence(reminder["REMINDER"])],
    "definition": next(line for line in body if line.strip()),
    "gate": first_sentence(gate["RULE_A_REASON"]),
}))
PY
  )" || return 1

  E2E_SUBAGENT_TEXT="$(jq -r '.subagent' <<<"$needles")"
  E2E_MAIN_TEXTS="$(jq -c '.main' <<<"$needles")"
  E2E_DEFINITION="$(jq -r '.definition' <<<"$needles")"
  E2E_GATE_TEXT="$(jq -r '.gate' <<<"$needles")"
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
# reminder> <subagent turns with python-pro's definition> <subagent turns
# carrying the Copilot no-write block> <subagent turns offered no write tool>
# <gate refusals of a main-thread write>". A subagent turn is a request the
# marker and the headers both place in the subagent and that offers tools.
# Each request repeats its session's history, so only zero or not zero
# matters for the counts of calls. An unreadable log counts as all zeros, so
# every check that needs a fact fails rather than passing on a parse error.
e2e_facts() {
  local log="$1" path="$2"

  jq -rs --arg path "$path" --argjson writes "$E2E_WRITE_TOOLS" --argjson spawns "$E2E_SPAWN_TOOLS" \
    --arg sub "$E2E_SUBAGENT_TEXT" --argjson mains "$E2E_MAIN_TEXTS" --arg def "$E2E_DEFINITION" \
    --arg nowrite "$E2E_COPILOT_NO_WRITE_MARKER" --arg gate "$E2E_GATE_TEXT" '
    def wrote: .calls[] | select((.name as $n | $writes | index($n)) and (.args | tojson | contains($path)));
    map(select(.role == "subagent" and .header_role == "subagent" and .tool_count > 0)) as $turns
    | [ (map(select(.role == "main") | [.calls[] | select((.name as $n | $spawns | index($n)) and .result != null)] | length) | add // 0),
        ($turns | map([wrote | select(.result != null)] | length) | add // 0),
        (map(select(.role == "main") | [wrote] | length) | add // 0),
        (map(select((.reply.text // "") | startswith("E2E: role conflict"))) | length),
        ($turns | length),
        ($turns | map(select(.context | contains($sub))) | length),
        ($turns | map(select(.context as $c | any($mains[]; . as $m | $c | contains($m)))) | length),
        ($turns | map(select(.system | contains($def))) | length),
        ($turns | map(select(.context | contains($nowrite))) | length),
        ($turns | map(select((.reply.text // "") | startswith("E2E: the request offers no write"))) | length),
        (map(select(.role == "main") | [wrote | select((.result // "") | contains($gate))] | length) | add // 0)
      ] | map(tostring) | join(" ")' "$log" 2>/dev/null || echo "0 0 0 0 0 0 0 0 0 0 0"
}

# The two scripted cases and every check, for one agent.
e2e_check_agent() {
  local agent="$1" project="$2"
  local dir="${E2E_TMP}/${agent}" status=0 records="" proof="" denied=""
  local spawns=0 sub_writes=0 main_writes=0 conflicts=0 turns=0 with_sub=0 with_main=0 with_def=0 nowrite=0 nowriter=0 refusals=0
  local rec_sub=0 rec_main=0

  e2e_identify "$agent"

  if ! command -v "$E2E_BIN" >/dev/null 2>&1; then
    fail "${E2E_LABEL} is installed as ${E2E_BIN} (not on PATH)"
    return
  fi

  e2e_prepare "$agent" "$project" "$dir"
  proof="${dir}/project/${E2E_PROOF}"
  denied="${dir}/project/${E2E_MAIN_PROOF}"

  e2e_invoke "$agent" "$dir" "E2E-SPAWN ${E2E_SUBAGENT} ${proof} ${E2E_CONTENT}" spawn || status=$?
  # Both verify scripts set IFS to newline and tab, so each read names its own separator.
  IFS=' ' read -r spawns sub_writes main_writes conflicts turns with_sub with_main with_def nowrite nowriter refusals \
    <<<"$(e2e_facts "${dir}/spawn.requests.jsonl" "$proof")"
  records="$(python3 -I -S "$E2E_RECORDS" "$agent" "${dir}/state" "$proof" 2>&1)" || records="unreadable: ${records}"
  IFS=' ' read -r rec_sub rec_main <<<"$records"

  if [[ -f "$proof" ]] && printf '%s\n' "$E2E_CONTENT" | cmp -s - "$proof"; then
    pass "${E2E_LABEL}: ${E2E_SUBAGENT} wrote ${E2E_PROOF} with the exact content"
  elif [[ ! -f "$proof" && "$agent" == "copilot" && "$nowrite" -gt 0 && "$nowriter" -gt 0 ]]; then
    e2e_known_gap "${E2E_LABEL}: ${E2E_SUBAGENT} was offered no write tool under the CLI's own subagent block (${E2E_COPILOT_NO_WRITE_MARKER}), as AGENTS.md records"
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

  if [[ "$turns" -gt 0 && "$with_sub" -eq "$turns" && "$with_main" -eq 0 ]]; then
    pass "${E2E_LABEL}: every subagent turn carries the subagent text and none the main-thread reminder (${turns} turns)"
  else
    fail "${E2E_LABEL}: every subagent turn carries the subagent text and none the main-thread reminder (${turns} turns, ${with_sub} with '${E2E_SUBAGENT_TEXT}', ${with_main} with a main-thread reminder)"
  fi

  status=0
  e2e_invoke "$agent" "$dir" "E2E-MAIN-WRITE ${denied} ${E2E_MAIN_CONTENT}" main-write || status=$?
  IFS=' ' read -r spawns sub_writes main_writes conflicts turns with_sub with_main with_def nowrite nowriter refusals \
    <<<"$(e2e_facts "${dir}/main-write.requests.jsonl" "$denied")"

  if [[ "$main_writes" -gt 0 && "$refusals" -gt 0 && ! -e "$denied" ]]; then
    pass "${E2E_LABEL}: the gate denies the main thread's own write, and the file was never created"
  elif [[ "$main_writes" -gt 0 && -e "$denied" && "$agent" == "copilot" ]]; then
    e2e_known_gap "${E2E_LABEL}: the main thread's own write landed, as AGENTS.md records: the Copilot preToolUse payload carries no agent identifier, so the gate cannot tell the main thread from a subagent"
  else
    fail "${E2E_LABEL}: the gate denies the main thread's own write (exit ${status}, ${main_writes} main-thread write call(s), ${refusals} carrying '${E2E_GATE_TEXT}', file present: $([[ -e "$denied" ]] && echo yes || echo no))"
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
