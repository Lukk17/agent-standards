#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: lib.sh
# Description: Shared library for the live agent tests. Sourced, never run. It
#              owns the provider health check, the throwaway project, the six
#              test cases and their verdicts. Each agent script supplies how to
#              configure, invoke and read back its own agent.
# Usage: source "$(dirname "$0")/lib.sh"; live_main "$@"
# Contract: the sourcing script defines these variables and functions.
#   AGENT_LABEL          Name printed in every line, e.g. claude-code.
#   AGENT_BIN            Command the agent is started with.
#   AGENT_NPM_PACKAGE    npm package whose pin is read from ../Dockerfile.
#   HEALTH_FORMAT        anthropic, responses or chat.
#   WRITE_TOOL_RE        Regex over tool names that can write a file.
#   SPAWN_TOOL_RE        Regex over tool names that start a subagent.
#   SKILL_TOOL_RE        Regex over tool names that load a skill.
#   GATE_KNOWN_GAP       1 when AGENTS.md documents that the gate cannot tell
#                        this agent's main thread from a subagent.
#   AGENT_PROVIDER       Optional, set before sourcing: requesty (the default)
#                        or openai, the API this agent's model is served from.
#   AGENT_MODEL          Optional, set before sourcing: the model id this agent
#                        runs, as its provider names it. Default DEFAULT_MODEL.
#   agent_configure      Writes the agent's CI-only provider configuration.
#   agent_invoke DIR P   Runs one headless prompt, keeps every transcript in DIR.
#   agent_calls DIR      Prints the recorded tool calls as NDJSON records of
#                        {actor, tool, input, result, error}.
#   agent_reminder_seen DIR NONCE
#                        Returns 0 when the per-prompt reminder reached the model.
#   agent_subagent_context DIR
#                        Prints the recorded context of every subagent the
#                        case started, and nothing the main thread recorded.
#   agent_model_error DIR
#                        Optional. Prints the error that ended the session when
#                        the provider rejected the agent's own model request,
#                        and returns non-zero when the session recorded none.
#   agent_mcp_servers DIR
#                        Optional. Prints one "name<TAB>status" line per MCP
#                        server the session knew, status "disabled" for one it
#                        left off, and returns non-zero when nothing records
#                        which servers the agent loaded.
# Environment:
#   REQUESTY_API_KEY     Requesty API key. Required on Requesty. Never printed.
#   OPENAI_API_KEY       OpenAI API key. Required on OpenAI. Never printed.
#   LIVE_WORK            Scratch directory. Default a fresh mktemp directory.
#   LIVE_INSTALL         1 installs the agent at the version the sandbox pins.
#   LIVE_AGENT_TIMEOUT   Seconds allowed per agent prompt. Default 600.
#   LIVE_ROUTER_URL      Requesty only. Default https://router.requesty.ai. The
#                        Anthropic format uses it bare, the OpenAI formats
#                        append /v1.
#   LIVE_MODEL           Overrides AGENT_MODEL for the agent being run.
# Exit codes:
#   0  No test failed. Inconclusive tests are reported but do not fail.
#   1  At least one test failed.
#   2  Misuse: unknown subcommand, missing command or missing provider key.
#   4  The provider health check failed, so no agent test ran.
# Requires: Bash 4.4 or newer, curl, jq, git, python3, timeout.
# -----------------------------------------------------------------------------
# shellcheck disable=SC2034  # constants read by the agent scripts that source this file

LIVE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_DIR="$(dirname "$LIVE_DIR")"
REPO_ROOT="$(dirname "$SANDBOX_DIR")"
readonly LIVE_DIR SANDBOX_DIR REPO_ROOT

readonly DEFAULT_MODEL="deepinfra/deepseek-v4-flash-0731"
readonly PROVIDER="${AGENT_PROVIDER:-requesty}"

case "$PROVIDER" in
  openai)
    PROVIDER_NAME="OpenAI"
    PROVIDER_KEY_VAR="OPENAI_API_KEY"
    PROVIDER_URL="https://api.openai.com"
    CHAT_TOKEN_LIMIT="max_completion_tokens"
    ;;
  *)
    PROVIDER_NAME="Requesty"
    PROVIDER_KEY_VAR="REQUESTY_API_KEY"
    PROVIDER_URL="${LIVE_ROUTER_URL:-https://router.requesty.ai}"
    CHAT_TOKEN_LIMIT="max_tokens"
    ;;
esac

readonly PROVIDER_NAME PROVIDER_KEY_VAR PROVIDER_URL CHAT_TOKEN_LIMIT
readonly PROVIDER_V1_URL="${PROVIDER_URL}/v1"
readonly MODEL="${LIVE_MODEL:-${AGENT_MODEL:-$DEFAULT_MODEL}}"
readonly AGENT_TIMEOUT="${LIVE_AGENT_TIMEOUT:-600}"

readonly GATE_SCRIPT="${REPO_ROOT}/.agents/hooks/preflight_gate.py"
readonly REMINDER_MARKER="End every reply to the user with this block, exactly as shown"
readonly SUBAGENT_TEXT_MARKER="PREFLIGHT for a subagent:"
readonly SUBAGENT_NAME="docs-architect"
readonly SKILL_NAME="kicad"
readonly MAIN_PROBE="live-probe/main-thread.txt"
readonly SUB_PROBE="live-probe/subagent-note.md"
readonly MCP_SERVER="context7"
readonly MCP_PROBE_LIBRARY="React"
readonly MCP_RESOLVE_TOOL_RE='context7.*resolve[-_]?library[-_]?id'
readonly MCP_ANSWER_RE='library ID: */[^/[:space:]]+/[^/[:space:]]+'

readonly EXIT_FAILED=1
readonly EXIT_USAGE=2
readonly EXIT_HEALTH=4

WORK=""
PROJECT=""
CASES=""
RESULTS=()
FAILURES=0
INCONCLUSIVE=0

log_info()  { printf '[INFO]  %s %s\n' "$AGENT_LABEL" "$*" >&2; }
log_error() { printf '[ERROR] %s %s\n' "$AGENT_LABEL" "$*" >&2; }

section() {
  printf '\n--------------------------------------------------------------\n'
  printf ' %s: %s\n' "$AGENT_LABEL" "$*"
  printf -- '--------------------------------------------------------------\n'
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [health|run|all] [-h|--help]

  health  Send one tiny request to ${PROVIDER_NAME} in the format ${AGENT_LABEL} uses.
  run     Run the agent tests (the health check runs first).
  all     Same as run. The default.

Requires ${PROVIDER_KEY_VAR} in the environment. See sandbox-agent/README.md.
EOF
}

require_commands() {
  local tool

  for tool in "$@"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      log_error "required command not found: ${tool}"
      return "$EXIT_USAGE"
    fi
  done
}

provider_key() {
  printf '%s' "${!PROVIDER_KEY_VAR:-}"
}

require_key() {
  if [[ -z "$(provider_key)" ]]; then
    log_error "${PROVIDER_KEY_VAR} is not set. Add it as a repository secret, or export it for a local run."
    return "$EXIT_USAGE"
  fi
}

# Records one verdict. $2 is PASS, FAIL, INCONCLUSIVE or KNOWN-GAP.
record() {
  local test_name="$1" verdict="$2" detail="$3"

  RESULTS+=("${verdict}|${test_name}|${detail}")
  printf '%-12s %s: %s (%s)\n' "$verdict" "$AGENT_LABEL" "$test_name" "$detail"

  case "$verdict" in
    FAIL) FAILURES=$((FAILURES + 1)) ;;
    INCONCLUSIVE) INCONCLUSIVE=$((INCONCLUSIVE + 1)) ;;
  esac

  if [[ -n "${GITHUB_ACTIONS:-}" && "$verdict" != "PASS" ]]; then
    local level="warning"
    [[ "$verdict" == "FAIL" ]] && level="error"
    printf '::%s title=%s %s::%s\n' "$level" "$AGENT_LABEL" "$verdict" "${test_name}: ${detail}"
  fi
}

# --- Provider health check ----------------------------------------------------

# Prints the request URL, one format-specific header and the body.
health_request() {
  case "$1" in
    anthropic)
      printf '%s\n' "${PROVIDER_V1_URL}/messages" "anthropic-version: 2023-06-01"
      jq -cn --arg m "$MODEL" '{model: $m, max_tokens: 16, messages: [{role: "user", content: "ping"}]}'
      ;;
    responses)
      printf '%s\n' "${PROVIDER_V1_URL}/responses" "Accept: application/json"
      jq -cn --arg m "$MODEL" '{model: $m, max_output_tokens: 16, input: "ping"}'
      ;;
    chat)
      printf '%s\n' "${PROVIDER_V1_URL}/chat/completions" "Accept: application/json"
      jq -cn --arg m "$MODEL" --arg limit "$CHAT_TOKEN_LIMIT" '{model: $m, ($limit): 16, messages: [{role: "user", content: "ping"}]}'
      ;;
    *)
      return "$EXIT_USAGE"
      ;;
  esac
}

# jq filter that is true when a 200 answer has the shape of the format.
health_shape() {
  case "$1" in
    anthropic) printf '%s' '(.content | type) == "array"' ;;
    responses) printf '%s' '(.output | type) == "array"' ;;
    chat) printf '%s' '(.choices | type) == "array"' ;;
  esac
}

# True when the provider cut the reply off at the token limit, which a
# reasoning model can hit on a 16-token ping: the model ran, so the key, the
# balance and the model all work.
stopped_at_token_limit() {
  [[ "${1,,}" == *"max_tokens or model output limit was reached"* ]]
}

# True when the provider's own message blames the model rather than the key.
message_names_model() {
  [[ "${1,,}" =~ model|access\ list|region|not\ supported|unsupported|unavailable|not\ available ]]
}

# Maps an HTTP status and Requesty's own message to one plain cause, following
# the error responses Requesty documents for its three inference endpoints.
health_cause_requesty() {
  local status="$1" message="$2"
  local invalid_key="the key was rejected: REQUESTY_API_KEY is invalid, revoked or empty"
  local no_model="the model ${MODEL} is not available to this key (not in the Requesty model list or the key's access list)"

  case "$status" in
    000) printf 'Requesty is unreachable: no HTTP answer from %s' "$ROUTER_URL" ;;
    401) printf '%s' "$invalid_key" ;;
    402) printf 'the Requesty balance is empty: top up the organization at https://app.requesty.ai' ;;
    403)
      if message_names_model "$message"; then
        printf '%s' "$no_model"
      else
        printf '%s' "$invalid_key"
      fi
      ;;
    404) printf '%s' "$no_model" ;;
    429) printf 'the upstream provider rate-limited the request (Requesty adds no limit of its own), retry later' ;;
    400)
      if message_names_model "$message"; then
        printf '%s' "$no_model"
      else
        printf 'Requesty rejected the request as malformed for this format'
      fi
      ;;
    5??) printf 'Requesty or the upstream provider is down (HTTP %s)' "$status" ;;
    *) printf 'Requesty answered HTTP %s' "$status" ;;
  esac
}

# Maps an HTTP status, OpenAI's error code and message, and any retry-after
# header to one plain cause, following the error codes OpenAI documents.
health_cause_openai() {
  local status="$1" message="$2" code="$3" retry_after="$4"
  local no_model="the model ${MODEL} does not exist on OpenAI or this key's project has no access to it (model_not_found)"
  local no_quota="the OpenAI quota is used up: add credit or raise the budget under Billing at https://platform.openai.com (insufficient_quota)"

  case "$status" in
    000) printf 'OpenAI is unreachable: no HTTP answer from %s' "$PROVIDER_URL" ;;
    401) printf 'the key was rejected: OPENAI_API_KEY is invalid, revoked or empty (invalid_api_key)' ;;
    403)
      if message_names_model "$message"; then
        printf '%s' "$no_model"
      else
        printf 'OpenAI refused this key from here: the country, region or project is not allowed'
      fi
      ;;
    404) printf '%s' "$no_model" ;;
    429)
      if [[ "$code" == "insufficient_quota" || "${message,,}" =~ quota|billing ]]; then
        printf '%s' "$no_quota"
      elif [[ -n "$retry_after" || "$code" == "rate_limit_exceeded" ]]; then
        printf 'OpenAI rate-limited the request, retry later'
      else
        printf '%s' "$no_quota"
      fi
      ;;
    400)
      if [[ "$code" == "model_not_found" ]] || message_names_model "$message"; then
        printf '%s' "$no_model"
      else
        printf 'OpenAI rejected the request as malformed for this format'
      fi
      ;;
    5??) printf 'OpenAI is down or overloaded (HTTP %s)' "$status" ;;
    *) printf 'OpenAI answered HTTP %s' "$status" ;;
  esac
}

# Sends one tiny request in the agent's wire format. The key reaches curl on
# stdin through --config, so it never appears in an argument list or a log.
health_check() {
  local format="$1"
  local url="" header="" body="" body_file="" header_file="" status="" message="" code="" retry_after="" cause=""
  local request=()

  mapfile -t request < <(health_request "$format")
  if [[ "${#request[@]}" -ne 3 ]]; then
    log_error "unknown health check format: ${format}"
    return "$EXIT_USAGE"
  fi
  url="${request[0]}"
  header="${request[1]}"
  body="${request[2]}"
  body_file="$(mktemp)"
  header_file="$(mktemp)"

  status="$(
    printf 'header = "Authorization: Bearer %s"\n' "$(provider_key)" |
      curl --silent --show-error --max-time 60 --connect-timeout 15 --config - \
        --header 'Content-Type: application/json' \
        --header "$header" \
        --dump-header "$header_file" \
        --output "$body_file" --write-out '%{http_code}' \
        --data "$body" "$url" 2>/dev/null
  )" || status="${status:-000}"

  message="$(jq -r '(.error.message? // .message? // .error? // empty) | tostring' "$body_file" 2>/dev/null | head -c 300 || true)"
  code="$(jq -r '(.error.code? // .error.type? // empty) | tostring' "$body_file" 2>/dev/null || true)"
  retry_after="$(grep -i '^retry-after:' "$header_file" 2>/dev/null | head -n 1 || true)"

  if [[ "$status" == "200" ]] && jq -e "$(health_shape "$format")" "$body_file" >/dev/null 2>&1; then
    rm -f "$body_file" "$header_file"
    printf 'HEALTH OK   %s: %s answered a %s request for %s\n' "$AGENT_LABEL" "$PROVIDER_NAME" "$format" "$MODEL"
    return 0
  fi

  if [[ "$status" == "400" ]] && stopped_at_token_limit "$message"; then
    rm -f "$body_file" "$header_file"
    printf 'HEALTH OK   %s: %s answered a %s request for %s, cut off at the token limit\n' "$AGENT_LABEL" "$PROVIDER_NAME" "$format" "$MODEL"
    return 0
  fi

  if [[ "$status" == "200" ]]; then
    cause="${PROVIDER_NAME} answered 200 but not in the ${format} shape, so this model does not serve that format"
  elif [[ "$PROVIDER" == "openai" ]]; then
    cause="$(health_cause_openai "$status" "$message" "$code" "$retry_after")"
  else
    cause="$(health_cause_requesty "$status" "$message")"
  fi

  rm -f "$body_file" "$header_file"
  printf 'HEALTH FAIL %s: %s. %s said: %s\n' "$AGENT_LABEL" "$cause" "$PROVIDER_NAME" "${message:-nothing}"

  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    printf '::error title=%s health check::%s\n' "$AGENT_LABEL" "$cause"
  fi

  return "$EXIT_HEALTH"
}

# --- Setup --------------------------------------------------------------------

# Prints the exact package spec the sandbox Dockerfile pins, the one source of
# truth for agent versions in this repository.
pinned_spec() {
  local package="$1" line

  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%\\}"
    line="${line%"${line##*[![:space:]]}"}"
    if [[ "$line" == "${package}@"* ]]; then
      printf '%s' "$line"
      return 0
    fi
  done < "${SANDBOX_DIR}/Dockerfile"

  log_error "no pin for ${package} in ${SANDBOX_DIR}/Dockerfile"
  return 1
}

install_agent() {
  local spec

  if [[ "${LIVE_INSTALL:-0}" != "1" ]]; then
    require_commands "$AGENT_BIN"
    return
  fi

  spec="$(pinned_spec "$AGENT_NPM_PACKAGE")"
  log_info "installing ${spec}"
  npm install --global --loglevel=error "$spec"
  require_commands "$AGENT_BIN"
}

prepare_workspace() {
  WORK="${LIVE_WORK:-$(mktemp -d -t "live-${AGENT_LABEL}-XXXXXXXX")}"
  mkdir -p "$WORK"
  WORK="$(cd "$WORK" && pwd)"
  PROJECT="${WORK}/project"
  CASES="${WORK}/cases"
  mkdir -p "$CASES"
  export GIT_CONFIG_GLOBAL="${WORK}/gitconfig"
}

# Builds the throwaway consumer project with the same import a consumer runs,
# so the agent sees exactly what a real project would receive.
prepare_project() {
  log_info "importing agent-standards into ${PROJECT}"
  AGENT_STANDARDS_REPO="$REPO_ROOT" SANDBOX_PROJECT="$PROJECT" bash "${SANDBOX_DIR}/setup-project.sh"
  git -C "$PROJECT" add --all
  git -C "$PROJECT" commit --quiet --message "import agent-standards"
}

# --- Evidence helpers ---------------------------------------------------------

# Counts recorded calls. $2 is main, subagent or any. $5 is 1 to count only
# calls that did not error.
count_calls() {
  local dir="$1" actor="$2" tool_re="$3" needle="$4" ok_only="${5:-0}"

  jq -s --arg a "$actor" --arg re "$tool_re" --arg n "$needle" --arg ok "$ok_only" '
    [ .[]
      | select($a == "any" or .actor == $a)
      | select(.tool | test($re))
      | select(.input | contains($n))
      | select($ok == "0" or (.error | not)) ]
    | length' "${dir}/calls.ndjson"
}

# Counts recorded calls of a tool matching $2 whose result also matches $3.
count_answered_calls() {
  local dir="$1" tool_re="$2" answer_re="$3"

  jq -s --arg re "$tool_re" --arg ans "$answer_re" '
    [ .[] | select(.tool | test($re; "i")) | select(.error | not) | select(.result | test($ans; "i")) ]
    | length' "${dir}/calls.ndjson"
}

# Prints the result of the first recorded call of a tool matching $2, on one
# line and cut short, so a verdict can quote the reason a call failed.
first_call_result() {
  local dir="$1" tool_re="$2"

  jq -s -r --arg re "$tool_re" '
    [ .[] | select(.tool | test($re; "i")) | .result ] | first // ""
    | gsub("[\\r\\n|]+"; " ") | .[0:200]' "${dir}/calls.ndjson"
}

# Prints the MCP_SERVER-only copy of an MCP file whose servers sit under key $2,
# the filtered configuration the live project runs with.
mcp_json_only_probe_server() {
  local file="$1" key="$2"

  jq -c --arg k "$key" --arg s "$MCP_SERVER" '{($k): {($s): .[$k][$s]}}' "$file"
}

# Prints every server name under key $2 of an MCP file except MCP_SERVER.
mcp_json_other_servers() {
  local file="$1" key="$2"

  jq -r --arg k "$key" --arg s "$MCP_SERVER" '.[$k] // {} | keys[] | select(. != $s)' "$file"
}

transcript_mentions() {
  grep -rqF --exclude=calls.ndjson -- "$2" "$1"
}

# Prints the fixed text of every deny reason the gate can give, one per line:
# the longest run of each RULE_*_REASON between its placeholders. Read from the
# gate itself, so a new rule or a reworded reason needs no change here.
gate_deny_markers() {
  local python

  python="$(command -v python3 || command -v python)" || return "$EXIT_USAGE"

  "$python" -S -E - "$GATE_SCRIPT" <<'EOF'
import importlib.util
import re
import sys

spec = importlib.util.spec_from_file_location("preflight_gate", sys.argv[1])
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

for name in sorted(vars(gate)):
    if re.fullmatch(r"RULE_[A-Z]+_REASON", name):
        print(max(re.split(r"\{[^{}]*\}", getattr(gate, name)), key=len).strip())
EOF
}

# Returns 0 when any gate deny reason appears in the recorded transcripts.
# Exits 2 when the gate's reasons cannot be read.
transcript_has_gate_denial() {
  local dir="$1" marker markers

  markers="$(gate_deny_markers)" || return "$EXIT_USAGE"
  [[ -n "$markers" ]] || return "$EXIT_USAGE"

  while IFS= read -r marker; do
    marker="${marker%$'\r'}"
    [[ -n "$marker" ]] || continue
    transcript_mentions "$dir" "$marker" && return 0
  done <<< "$markers"

  return 1
}

new_files_since() {
  local root="$1" snapshot="$2"

  [[ -d "$root" ]] || return 0
  comm -13 "$snapshot" <(find "$root" -type f | sort)
}

snapshot_files() {
  local root="$1" snapshot="$2"

  if [[ -d "$root" ]]; then
    find "$root" -type f | sort > "$snapshot"
  else
    : > "$snapshot"
  fi
}

run_case() {
  local id="$1" prompt="$2"
  local dir="${CASES}/${id}"

  mkdir -p "$dir"
  printf '%s\n' "$prompt" > "${dir}/prompt.txt"
  log_info "case ${id}: running the prompt"

  if ! (cd "$PROJECT" && agent_invoke "$dir" "$prompt"); then
    log_info "case ${id}: the agent exited non-zero, reading whatever it recorded"
  fi

  agent_calls "$dir" > "${dir}/calls.ndjson" 2>"${dir}/calls.err" || true
}

# Records FAIL and returns 0 when the agent says the provider rejected its own
# model request, so a model that never ran is not read as one that chose not to
# act, and a reminder that sat in a rejected request does not count as seen.
record_model_failure() {
  local name="$1" dir="$2" error

  declare -F agent_model_error > /dev/null || return 1
  error="$(agent_model_error "$dir" 2>/dev/null)" || return 1
  [[ -n "$error" ]] || return 1

  record "$name" FAIL "the provider rejected the agent's model request, so the model never ran: ${error//|//}"
}

# --- The six tests ------------------------------------------------------------

test_gate_blocks_main_thread() {
  local name="1 main-thread write is blocked by the preflight gate" dir="${CASES}/1-gate"
  local attempts sub_writes denial=0

  run_case "1-gate" "Create a new file at ${MAIN_PROBE} containing the single line: probe. Write it yourself, right now, with your own file-writing tool. Do not delegate to a subagent and do not ask any question. Stop after the attempt whatever the outcome."
  record_model_failure "$name" "$dir" && return

  attempts="$(count_calls "$dir" main "$WRITE_TOOL_RE" "main-thread.txt")"
  sub_writes="$(count_calls "$dir" subagent "$WRITE_TOOL_RE" "main-thread.txt" 1)"
  transcript_has_gate_denial "$dir" || denial=$?

  if [[ "$attempts" -eq 0 ]]; then
    record "$name" INCONCLUSIVE "the model never attempted a main-thread write of ${MAIN_PROBE}"
  elif [[ -e "${PROJECT}/${MAIN_PROBE}" && "$GATE_KNOWN_GAP" == "1" ]]; then
    record "$name" KNOWN-GAP "the write landed, as AGENTS.md documents: this surface carries no agent identifier"
  elif [[ -e "${PROJECT}/${MAIN_PROBE}" && "$sub_writes" -gt 0 && "$denial" -eq 0 ]]; then
    record "$name" PASS "the gate denied the main thread, then the model delegated and ${sub_writes} subagent write(s) created ${MAIN_PROBE}"
  elif [[ -e "${PROJECT}/${MAIN_PROBE}" ]]; then
    record "$name" FAIL "${attempts} main-thread write attempt(s) and ${MAIN_PROBE} was created, the gate let it through"
  elif [[ "$denial" -eq "$EXIT_USAGE" ]]; then
    record "$name" FAIL "the deny reasons could not be read from ${GATE_SCRIPT}"
  elif [[ "$denial" -eq 0 ]]; then
    record "$name" PASS "${attempts} main-thread write attempt(s), all denied by the gate, file absent"
  else
    record "$name" FAIL "the write did not land, but no preflight gate denial was recorded"
  fi
}

test_subagent_writes_file() {
  local name="2 a named subagent writes the file" dir="${CASES}/2-subagent"
  local spawn_attempts spawns sub_writes main_writes context

  run_case "2-subagent" "Delegate this task to the ${SUBAGENT_NAME} subagent: create the file ${SUB_PROBE} containing the single line: written by subagent. Do not write the file yourself. Stop once the subagent has reported back."
  record_model_failure "$name" "$dir" && return

  spawn_attempts="$(count_calls "$dir" main "$SPAWN_TOOL_RE" "$SUBAGENT_NAME")"
  spawns="$(count_calls "$dir" main "$SPAWN_TOOL_RE" "$SUBAGENT_NAME" 1)"
  sub_writes="$(count_calls "$dir" subagent "$WRITE_TOOL_RE" "subagent-note.md" 1)"
  main_writes="$(count_calls "$dir" main "$WRITE_TOOL_RE" "subagent-note.md" 1)"
  context="$(agent_subagent_context "$dir" 2>/dev/null || true)"

  if [[ "$spawn_attempts" -eq 0 ]]; then
    record "$name" INCONCLUSIVE "the model never started the ${SUBAGENT_NAME} subagent"
  elif [[ "$spawns" -eq 0 ]]; then
    record "$name" FAIL "the agent rejected all ${spawn_attempts} call(s) to start ${SUBAGENT_NAME}, so the subagent never ran"
  elif [[ ! -f "${PROJECT}/${SUB_PROBE}" ]]; then
    record "$name" FAIL "${SUBAGENT_NAME} was started but ${SUB_PROBE} does not exist"
  elif [[ "$context" != *"$SUBAGENT_TEXT_MARKER"* ]]; then
    record "$name" FAIL "the subagent's transcript does not carry the subagent text (${SUBAGENT_TEXT_MARKER})"
  elif [[ "$context" == *"$REMINDER_MARKER"* ]]; then
    record "$name" FAIL "the subagent's transcript carries the main-thread reminder, which tells it to delegate"
  elif [[ "$sub_writes" -gt 0 ]]; then
    record "$name" PASS "${SUB_PROBE} exists and ${sub_writes} successful write(s) came from the subagent"
  elif [[ "$main_writes" -gt 0 ]]; then
    record "$name" FAIL "${SUB_PROBE} exists but the main thread wrote it"
  else
    record "$name" FAIL "${SUB_PROBE} exists but no recorded subagent write names it"
  fi
}

test_skill_is_loaded() {
  local name="3 the task loads the ${SKILL_NAME} skill" dir="${CASES}/3-skill"
  local needle="skills/${SKILL_NAME}/SKILL.md" attempts loaded

  run_case "3-skill" "Before answering, load the project skill that owns KiCad board design, using your skill tool if you have one or by reading its SKILL.md. Then say in one sentence what that skill recommends for ground pours. Do not create or edit any file."
  record_model_failure "$name" "$dir" && return

  attempts="$(( $(count_calls "$dir" main "$SKILL_TOOL_RE" "$SKILL_NAME") + $(count_calls "$dir" main '.' "$needle") ))"
  loaded="$(( $(count_calls "$dir" main "$SKILL_TOOL_RE" "$SKILL_NAME" 1) + $(count_calls "$dir" main '.' "$needle" 1) ))"

  if [[ "$attempts" -eq 0 ]]; then
    record "$name" INCONCLUSIVE "the model never tried to load the ${SKILL_NAME} skill"
  elif [[ "$loaded" -gt 0 ]]; then
    record "$name" PASS "${loaded} successful load(s) of the ${SKILL_NAME} skill"
  else
    record "$name" FAIL "${attempts} attempt(s) to load the ${SKILL_NAME} skill, every one errored"
  fi
}

test_reminder_reaches_model() {
  local name="4 the per-prompt reminder reaches the model" dir="${CASES}/4-reminder"
  local nonce="live-nonce-${RANDOM}${RANDOM}"

  run_case "4-reminder" "Reply with the single word ready followed by the token ${nonce}. Do not use any tool."
  record_model_failure "$name" "$dir" && return

  if agent_reminder_seen "$dir" "$nonce"; then
    record "$name" PASS "the reminder text is in the recorded context of the prompt"
  else
    record "$name" FAIL "no recorded context carries the reminder text"
  fi
}

# Prints why the loaded MCP servers are wrong, or nothing when the session
# loaded MCP_SERVER alone. Returns 1 when the agent records no server list.
mcp_server_set_problem() {
  local dir="$1" servers others probe_status

  declare -F agent_mcp_servers > /dev/null || return 1
  servers="$(agent_mcp_servers "$dir" 2>/dev/null)" || return 1

  others="$(awk -F '\t' -v s="$MCP_SERVER" '$1 != s && $2 != "disabled" { printf "%s%s", sep, $1; sep = ", " }' <<< "$servers")"
  probe_status="$(awk -F '\t' -v s="$MCP_SERVER" '$1 == s { print $2; exit }' <<< "$servers")"

  if [[ -n "$others" ]]; then
    printf 'the session loaded MCP servers besides %s: %s' "$MCP_SERVER" "$others"
  elif [[ -z "$probe_status" ]]; then
    printf 'the session did not load the %s MCP server' "$MCP_SERVER"
  elif [[ "${probe_status,,}" =~ fail|error|disabled|auth ]]; then
    printf 'the %s MCP server did not start (%s)' "$MCP_SERVER" "$probe_status"
  fi
}

test_mcp_server_answers() {
  local name="6 the ${MCP_SERVER} MCP server is the only one and answers" dir="${CASES}/6-mcp"
  local attempts answered problem="" listed=0

  run_case "6-mcp" "Use the resolve-library-id tool of the ${MCP_SERVER} MCP server to look up the ${MCP_SERVER} library id for ${MCP_PROBE_LIBRARY}. Call that tool yourself, right now: do not delegate to a subagent, do not use any other tool, and do not create or edit any file. Then reply with the library id it returned."
  record_model_failure "$name" "$dir" && return

  problem="$(mcp_server_set_problem "$dir")" || listed=$?
  attempts="$(count_calls "$dir" any "$MCP_RESOLVE_TOOL_RE" "")"
  answered="$(count_answered_calls "$dir" "$MCP_RESOLVE_TOOL_RE" "$MCP_ANSWER_RE")"

  if [[ -n "$problem" ]]; then
    record "$name" FAIL "$problem"
  elif [[ "$attempts" -eq 0 ]]; then
    record "$name" INCONCLUSIVE "the model never called the ${MCP_SERVER} resolve-library-id tool"
  elif [[ "$answered" -gt 0 && "$listed" -eq 0 ]]; then
    record "$name" PASS "${MCP_SERVER} was the only MCP server loaded and ${answered} resolve-library-id call(s) returned a library id"
  elif [[ "$answered" -gt 0 ]]; then
    record "$name" PASS "${answered} ${MCP_SERVER} resolve-library-id call(s) returned a library id, the transcript does not list the loaded servers"
  else
    record "$name" FAIL "${attempts} ${MCP_SERVER} resolve-library-id call(s), none returned a library id: $(first_call_result "$dir" "$MCP_RESOLVE_TOOL_RE")"
  fi
}

# --- Reporting ----------------------------------------------------------------

write_step_summary() {
  local entry verdict test_name detail

  [[ -n "${GITHUB_STEP_SUMMARY:-}" ]] || return 0

  {
    printf '### %s against %s\n\n' "$AGENT_LABEL" "$MODEL"
    printf '| Verdict | Test | Evidence |\n| --- | --- | --- |\n'
    for entry in "${RESULTS[@]}"; do
      IFS='|' read -r verdict test_name detail <<< "$entry"
      printf '| %s | %s | %s |\n' "$verdict" "$test_name" "$detail"
    done
    printf '\n'
  } >> "$GITHUB_STEP_SUMMARY"
}

# Drops any recorded file that contains the key, so an uploaded artifact can
# never carry it even if an agent logged its own request headers.
scrub_transcripts() {
  local leaked

  while IFS= read -r leaked; do
    [[ -n "$leaked" ]] || continue
    log_error "removing a transcript that contains the key: ${leaked#"${WORK}/"}"
    rm -f -- "$leaked"
  done < <(grep -rlF -- "$(provider_key)" "$WORK" 2>/dev/null || true)
}

summary() {
  section "result"
  printf 'Failed: %d  Inconclusive: %d  Transcripts: %s\n' "$FAILURES" "$INCONCLUSIVE" "$CASES"
  write_step_summary
  scrub_transcripts

  if [[ "$FAILURES" -gt 0 ]]; then
    return "$EXIT_FAILED"
  fi
}

run_suite() {
  local health_status=0

  section "5 key and model check"
  health_check "$HEALTH_FORMAT" || health_status=$?
  if [[ "$health_status" -ne 0 ]]; then
    return "$health_status"
  fi
  record "5 key and model answer through ${PROVIDER_NAME}" PASS "${HEALTH_FORMAT} request for ${MODEL} answered"

  install_agent
  prepare_workspace
  prepare_project
  agent_configure

  section "1 to 4 and 6 against the real model"
  test_gate_blocks_main_thread
  test_subagent_writes_file
  test_skill_is_loaded
  test_reminder_reaches_model
  test_mcp_server_answers

  summary
}

live_main() {
  local command="${1:-all}"

  case "$command" in
    -h|--help) usage; return 0 ;;
    health|run|all) ;;
    *) usage >&2; return "$EXIT_USAGE" ;;
  esac

  require_commands curl jq git python3 timeout comm find || return
  require_key || return

  if [[ "$command" == "health" ]]; then
    health_check "$HEALTH_FORMAT"
    return
  fi

  run_suite
}
