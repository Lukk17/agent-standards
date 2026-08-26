#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: verify-global.sh
# Description: Asserts that every supported agent discovers the shared skills,
#              its own subagent tree, its preflight wiring and its MCP servers
#              from the container's home directory, judged from a bare working
#              directory that holds none of the per-project files, and that the
#              preflight gate really denies from there. Global counterpart of
#              verify-project.sh; the assertions are those of the global specs
#              6 to 9 under e2e/testing.
# Usage: verify-global.sh [--scoped AGENT]
# Options:
#   --scoped AGENT  Install for that agent alone and assert that only its own
#                   paths were written. Agents: claude, codex, opencode, kilo,
#                   copilot.
# Environment:
#   AGENT_STANDARDS_REPO Mounted upstream repository. Default /repo.
#   SANDBOX_BARE         Bare working directory. Default /work/bare.
#   SANDBOX_CLI_TIMEOUT  Seconds allowed per agent CLI call. Default 300.
# Exit codes:
#   0  Every assertion passed.
#   1  At least one assertion failed.
#   2  Bad arguments.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly REPO="${AGENT_STANDARDS_REPO:-/repo}"
readonly BARE="${SANDBOX_BARE:-/work/bare}"
readonly SETUP="/sandbox/setup-global.sh"
readonly CLI_TIMEOUT="${SANDBOX_CLI_TIMEOUT:-300}"
readonly GATE="${HOME}/.agents/hooks/preflight_gate.py"
readonly PROBE_NAME="e2e-no-skills-probe"
readonly PROBE_AGENT="${HOME}/.claude/agents/${PROBE_NAME}.md"
readonly FIXTURES="${REPO}/e2e/fixtures"
readonly PAYLOADS="${FIXTURES}/gate-payloads"
readonly GLOBAL_FIXTURES="${FIXTURES}/global"

# The per-project files whose presence in the working directory would make every
# other assertion in this script unattributable to the home layer.
readonly PROJECT_MARKERS=(
  ".agents"
  ".claude"
  ".codex"
  ".github"
  ".kilo"
  ".opencode"
  ".vscode"
  ".mcp.json"
  "opencode.json"
  "AGENTS.md"
)

# Every directory the install writes to, cleared before a run so the script is
# re-runnable in a container that has already run it once. ~/.claude.json is on
# the list because `claude mcp add` writes user-scope servers there.
readonly INSTALL_PATHS=(
  "${HOME}/.agent-standards"
  "${HOME}/.agents"
  "${HOME}/.claude"
  "${HOME}/.claude.json"
  "${HOME}/.codex"
  "${HOME}/.config/opencode"
  "${HOME}/.config/kilo"
  "${HOME}/.copilot"
)

# Paths each agent owns, used by --scoped to assert that installing for one
# agent writes that agent's paths and none of the other four's.
readonly CLAUDE_PATHS=(".claude/skills" ".claude/agents" ".claude/settings.json" ".claude/CLAUDE.md")
readonly CODEX_PATHS=(".codex/agents" ".codex/AGENTS.md" ".codex/hooks.json")
readonly OPENCODE_PATHS=(".config/opencode/agents" ".config/opencode/plugins" ".config/opencode/AGENTS.md")
readonly KILO_PATHS=(".config/kilo/agents" ".config/kilo/plugin" ".config/kilo/kilo.jsonc")
readonly COPILOT_PATHS=(".copilot/agents" ".copilot/hooks" ".copilot/copilot-instructions.md")

# Every agent CLI is captured into this file rather than into a pipe. OpenCode
# exits without draining a large stdout when stdout is a pipe, which silently
# truncates the listing mid-line while still exiting 0. See README.md.
CLI_OUTPUT="$(mktemp -t sandbox-cli-XXXXXXXX)"
readonly CLI_OUTPUT

# Every capture is also appended here, so a single assertion can be made over a
# group of listings. It is emptied at the start of each group that needs one.
CLI_ARCHIVE="$(mktemp -t sandbox-archive-XXXXXXXX)"
readonly CLI_ARCHIVE

PASSES=0
FAILURES=0
SCOPED=""

SKILL_FILE_COUNT=0
SKILLS=()
SUBAGENTS=()

FIRST_INSTALL_STATUS=0
SECOND_INSTALL_STATUS=0

cleanup() {
  local exit_code=$?

  rm -f "$CLI_OUTPUT" "$CLI_ARCHIVE"

  exit "$exit_code"
}
trap cleanup EXIT

pass() { printf 'PASS  %s\n' "$*"; PASSES=$((PASSES + 1)); }
fail() { printf 'FAIL  %s\n' "$*"; FAILURES=$((FAILURES + 1)); }
note() { printf 'NOTE  %s\n' "$*"; }

section() {
  printf '\n--------------------------------------------------------------\n'
  printf ' %s\n' "$*"
  printf -- '--------------------------------------------------------------\n'
}

# Joins its arguments with ", " so a failure fits on one reported line.
join_commas() {
  local joined=""

  joined="$(printf '%s, ' "$@")"

  printf '%s' "${joined%, }"
}

# Collapses multi-line command output into the last few lines on one line.
one_line() {
  printf '%s' "$1" | tail -n 3 | tr '\n' ' ' | tr -s ' '
}

# Collapses the tail of the captured CLI output onto one line.
one_line_capture() {
  one_line "$(tail -n 3 "$CLI_OUTPUT")"
}

# --- Argument parsing --------------------------------------------------------

usage() {
  sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --scoped)
        [[ $# -ge 2 ]] || { printf 'FAIL  --scoped needs an agent name\n'; exit 2; }
        SCOPED="$2"
        shift 2
        ;;
      --scoped=*)
        SCOPED="${1#*=}"
        shift
        ;;
      *)
        printf 'FAIL  unknown argument: %s\n' "$1"
        exit 2
        ;;
    esac
  done

  case "${SCOPED:-none}" in
    none|claude|codex|opencode|kilo|copilot) ;;
    *)
      printf 'FAIL  unknown agent for --scoped: %s\n' "$SCOPED"
      exit 2
      ;;
  esac
}

# --- Assertion helpers -------------------------------------------------------
#
# Every path argument is relative to the container's home directory, which is
# what the global install writes into. Nothing here is ever piped to, because a
# pipe would run the counters in a subshell and discard both the pass and the
# failure.

assert_file() {
  local label="$1" path="$2"

  if [[ -f "${HOME}/${path}" ]]; then
    pass "${label} (~/${path})"
  else
    fail "${label} (~/${path} is missing)"
  fi
}

assert_file_not_empty() {
  local label="$1" path="$2"

  if [[ -s "${HOME}/${path}" ]]; then
    pass "${label} (~/${path})"
  else
    fail "${label} (~/${path} is missing or empty)"
  fi
}

assert_absent() {
  local label="$1" path="$2"

  if [[ -e "${HOME}/${path}" ]]; then
    fail "${label} (~/${path} should not be here)"
  else
    pass "${label} (~/${path} was not written)"
  fi
}

assert_present() {
  local label="$1" path="$2"

  if [[ -e "${HOME}/${path}" ]]; then
    pass "${label} (~/${path})"
  else
    fail "${label} (~/${path} is missing)"
  fi
}

assert_symlinked_dir() {
  local label="$1" path="$2"

  if [[ -L "${HOME}/${path}" && -d "${HOME}/${path}" ]]; then
    pass "${label} (~/${path} points at $(readlink "${HOME}/${path}"))"
  else
    fail "${label} (~/${path} is not a symlink that resolves to a directory)"
  fi
}

assert_symlinked_file() {
  local label="$1" path="$2"

  if [[ -L "${HOME}/${path}" && -f "${HOME}/${path}" ]]; then
    pass "${label} (~/${path} points at $(readlink "${HOME}/${path}"))"
  else
    fail "${label} (~/${path} is not a symlink that resolves to a file)"
  fi
}

assert_glob_count() {
  local label="$1" pattern="$2" expected="$3"
  local matches=()

  shopt -s nullglob
  # shellcheck disable=SC2206
  matches=( ${HOME}/${pattern} )
  shopt -u nullglob

  if [[ "${#matches[@]}" -eq "$expected" ]]; then
    pass "${label} (${#matches[@]} of ${expected})"
  else
    fail "${label} (found ${#matches[@]}, expected ${expected})"
  fi
}

assert_line_count() {
  local label="$1" path="$2" line="$3" expected="$4"
  local found=0

  if [[ -f "${HOME}/${path}" ]]; then
    found="$(grep -cxF -- "$line" "${HOME}/${path}" || true)"
  fi

  if [[ "$found" -eq "$expected" ]]; then
    pass "${label} (${found} of ${expected})"
  else
    fail "${label} (~/${path} carries the line ${found} time(s), expected ${expected})"
  fi
}

assert_json() {
  local label="$1" path="$2" filter="$3"
  local result=""

  if [[ ! -f "${HOME}/${path}" ]]; then
    fail "${label} (~/${path} is missing)"
    return
  fi

  result="$(jq -r "$filter" "${HOME}/${path}" 2>/dev/null || echo "error")"

  if [[ "$result" == "true" ]]; then
    pass "${label}"
  else
    fail "${label} (the check over ~/${path} returned '${result}')"
  fi
}

# Passes when the file exists and does not carry the needle.
assert_file_lacks() {
  local label="$1" path="$2" needle="$3"

  if [[ ! -f "${HOME}/${path}" ]]; then
    fail "${label} (~/${path} is missing)"
    return
  fi

  if grep -qF -- "$needle" "${HOME}/${path}"; then
    fail "${label} (~/${path} still carries '${needle}')"
  else
    pass "${label}"
  fi
}

# Passes when the working directory holds none of the per-project files. Every
# other assertion in this script depends on it, so it is asserted first and
# again before each group that reads an agent's own answer.
assert_bare_working_directory() {
  local label="$1"
  local offenders=() marker=""

  for marker in "${PROJECT_MARKERS[@]}"; do
    if [[ -e "${BARE}/${marker}" ]]; then
      offenders+=("$marker")
    fi
  done

  if [[ "${#offenders[@]}" -eq 0 ]]; then
    pass "${label} (${BARE} holds none of them)"
  else
    fail "${label} (${BARE} holds: $(join_commas "${offenders[@]}"))"
  fi
}

assert_status() {
  local label="$1" actual="$2" expected="$3"

  if [[ "$actual" -eq "$expected" ]]; then
    pass "${label} (exit ${actual})"
  else
    fail "${label} (exit ${actual}, expected ${expected})"
  fi
}

# --- Agent CLI helpers -------------------------------------------------------

archive_reset() {
  : >"$CLI_ARCHIVE"
}

# Runs an agent CLI from the bare working directory with stdout and stderr
# captured into CLI_OUTPUT, then appends that capture to CLI_ARCHIVE. Returns
# the exit status the CLI reported.
capture_cli() {
  local status=0

  (cd "$BARE" && timeout "$CLI_TIMEOUT" "$@" </dev/null >"$CLI_OUTPUT" 2>&1) || status=$?

  cat "$CLI_OUTPUT" >>"$CLI_ARCHIVE"

  return "$status"
}

# Runs an agent CLI from the bare working directory and passes when every needle
# appears in its output. Needles arrive on stdin, one per line, so the call must
# be redirected rather than piped, because a pipe would run the counters in a
# subshell and drop both the pass and the failure.
assert_cli_lists() {
  local label="$1"
  shift
  local needles=()
  local status=0 missing=() needle=""

  mapfile -t needles < <(cat)

  capture_cli "$@" || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "${label} (${1} exited ${status}: $(one_line_capture))"
    return
  fi

  for needle in "${needles[@]}"; do
    if ! grep -qF -- "$needle" "$CLI_OUTPUT"; then
      missing+=("$needle")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    pass "${label} (${#needles[@]} of ${#needles[@]} listed by ${1})"
  else
    fail "${label} (${1} did not list: $(join_commas "${missing[@]}"))"
  fi
}

# Passes when the CLI runs and its output does not contain the needle.
assert_cli_lacks() {
  local label="$1" needle="$2"
  shift 2
  local status=0

  capture_cli "$@" || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "${label} (${1} exited ${status}: $(one_line_capture))"
    return
  fi

  if grep -qF -- "$needle" "$CLI_OUTPUT"; then
    fail "${label} (${1} reported: $(one_line "$(grep -m1 -A2 -F -- "$needle" "$CLI_OUTPUT")"))"
  else
    pass "${label}"
  fi
}

# Same as assert_cli_lacks for a case-insensitive extended regular expression,
# which is how a load or parse failure has to be matched because the wording
# differs between the two halves of the phrase.
assert_cli_lacks_matching() {
  local label="$1" pattern="$2"
  shift 2
  local status=0

  capture_cli "$@" || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "${label} (${1} exited ${status}: $(one_line_capture))"
    return
  fi

  if grep -qiE -- "$pattern" "$CLI_OUTPUT"; then
    fail "${label} (${1} reported: $(one_line "$(grep -m1 -iE -- "$pattern" "$CLI_OUTPUT")"))"
  else
    pass "${label}"
  fi
}

# Passes when none of the captures collected since the last archive_reset
# carries the needle.
assert_archive_lacks() {
  local label="$1" needle="$2"

  if grep -qF -- "$needle" "$CLI_ARCHIVE"; then
    fail "${label} (a listing named '${needle}')"
  else
    pass "${label}"
  fi
}

# --- Install -----------------------------------------------------------------

reset_global() {
  local path

  for path in "${INSTALL_PATHS[@]}"; do
    rm -rf "$path"
  done

  rm -rf "$BARE"
  mkdir -p "$BARE"
}

install_global() {
  section "Global install"

  note "the installer reads ${REPO} and writes into ${HOME}."

  "$SETUP" "$@" || FIRST_INSTALL_STATUS=$?

  if [[ $# -eq 0 ]]; then
    "$SETUP" || SECOND_INSTALL_STATUS=$?
  fi
}

# --- Spec 6, install shape ---------------------------------------------------

collect_canonical() {
  mapfile -t SUBAGENTS < <(find "${REPO}/.agents/agents" -maxdepth 1 -name '*.md' -printf '%f\n' | sed 's/\.md$//' | sort)
  mapfile -t SKILLS < <(find "${REPO}/.agents/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
  SKILL_FILE_COUNT="$(find "${REPO}/.agents/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)"
}

verify_install_shape() {
  section "Install shape, home directory"

  assert_status "the first install exited 0" "$FIRST_INSTALL_STATUS" 0
  assert_status "the second install exited 0, so re-running is the update path" "$SECOND_INSTALL_STATUS" 0

  assert_bare_working_directory "the working directory holds none of the per-project files"

  assert_glob_count "the shared skills tree holds every canonical skill" \
    ".agents/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_symlinked_dir "Claude Code's skills location resolves to a directory" ".claude/skills"
  assert_glob_count "the same skill count is reachable through that symlink" \
    ".claude/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_file "the gate script landed in the shared tree" ".agents/hooks/preflight_gate.py"

  assert_glob_count "Claude Code has every subagent in its own markdown format" \
    ".claude/agents/*.md" "${#SUBAGENTS[@]}"
  assert_glob_count "Codex has every subagent in TOML" \
    ".codex/agents/*.toml" "${#SUBAGENTS[@]}"
  assert_glob_count "OpenCode has every subagent in its own global location" \
    ".config/opencode/agents/*.md" "${#SUBAGENTS[@]}"
  assert_glob_count "Kilo Code has every subagent in its own global location" \
    ".config/kilo/agents/*.md" "${#SUBAGENTS[@]}"
  assert_glob_count "GitHub Copilot has every subagent as *.agent.md" \
    ".copilot/agents/*.agent.md" "${#SUBAGENTS[@]}"

  assert_absent "the second install nested no tree inside the Claude Code one" ".claude/agents/agents"
  assert_absent "the second install nested no tree inside the OpenCode one" ".config/opencode/agents/agents"
  assert_absent "the second install nested no tree inside the Kilo Code one" ".config/kilo/agents/agents"

  assert_file_not_empty "there is one shared instruction file" ".agents/AGENTS.md"
  assert_line_count "Claude Code points at it with exactly one import line" \
    ".claude/CLAUDE.md" "@~/.agents/AGENTS.md" 1
  assert_symlinked_file "Codex points at it with a symlink" ".codex/AGENTS.md"
  assert_symlinked_file "OpenCode points at it with a symlink" ".config/opencode/AGENTS.md"
  assert_symlinked_file "Copilot points at it with a symlink" ".copilot/copilot-instructions.md"
  assert_json "Kilo Code points at it through its instructions key" ".config/kilo/kilo.jsonc" \
    '[.instructions[]] | any(contains(".agents/AGENTS.md"))'
  assert_json "Kilo Code is told where the shared skills tree is" ".config/kilo/kilo.jsonc" \
    '[.skills.paths[]] | any(contains(".agents/skills"))'

  assert_json "Claude Code's user settings call the gate by absolute path" ".claude/settings.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format claude"))'
  assert_json "Codex's user hooks call the gate by absolute path" ".codex/hooks.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format codex"))'
  assert_json "Copilot's user hooks call the gate by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks.preToolUse[].bash] | any(contains("/.agents/hooks/preflight_gate.py --format copilot"))'
  assert_file_lacks "no project-relative gate call survived the rewrite" \
    ".copilot/hooks/preflight.json" "python .agents/hooks/preflight_gate.py"

  assert_file "the plugin shim landed where OpenCode loads one" ".config/opencode/plugins/hooks.js"
  assert_file "the plugin shim landed where Kilo Code loads one" ".config/kilo/plugin/hooks.js"
}

# --- Spec 7, agent discovery -------------------------------------------------

verify_agent_discovery() {
  section "Agent discovery from a bare directory"

  assert_bare_working_directory "the working directory still holds none of the per-project files"

  assert_cli_lists "OpenCode itself names every subagent the global install placed" opencode agent list \
    < <(printf '%s\n' "${SUBAGENTS[@]}")
  assert_cli_lists "Kilo Code itself names every subagent from its own global location" kilocode agent list \
    < <(printf '%s\n' "${SUBAGENTS[@]}")
  assert_cli_lacks "Kilo Code accepts the global configuration instead of rejecting it" \
    "Configuration is invalid" kilocode config check
  assert_cli_lists "Copilot itself loads every skill in the shared tree" copilot skill list \
    < <(printf '%s\n' "${SKILLS[@]}")
  assert_cli_lacks_matching "every skill in the shared tree parses for Copilot" \
    "failed to (load|parse)" copilot skill list
}

# --- Spec 8, MCP visibility --------------------------------------------------

# Names of the servers a fixture file declares, one per line.
fixture_servers() {
  local path="$1" kind="$2"

  case "$kind" in
    toml)
      python3 -c 'import sys, tomllib; print("\n".join(sorted(tomllib.load(open(sys.argv[1], "rb"))["mcp_servers"])))' "$path"
      ;;
    *)
      jq -r "${kind} | keys[]" "$path"
      ;;
  esac
}

install_user_scope_mcp() {
  note "the installer writes no MCP configuration, deliberately, so the fixtures place every server here."

  cp "${GLOBAL_FIXTURES}/codex-config.toml" "${HOME}/.codex/config.toml"
  cp "${GLOBAL_FIXTURES}/opencode.json" "${HOME}/.config/opencode/opencode.json"
  cp "${GLOBAL_FIXTURES}/kilo.jsonc" "${HOME}/.config/kilo/kilo.jsonc"
  cp "${GLOBAL_FIXTURES}/copilot-mcp-config.json" "${HOME}/.copilot/mcp-config.json"

  (cd "$BARE" && timeout "$CLI_TIMEOUT" claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp </dev/null >/dev/null 2>&1)
}

verify_mcp_visibility() {
  section "MCP visibility from a bare directory"

  install_user_scope_mcp
  archive_reset

  assert_bare_working_directory "the working directory still holds none of the per-project files"

  assert_cli_lists "Claude Code itself names the server added at user scope" claude mcp list \
    < <(printf 'context7\n')
  assert_cli_lists "Codex itself names every server its user-scope file declares" codex mcp list \
    < <(fixture_servers "${GLOBAL_FIXTURES}/codex-config.toml" toml)
  assert_cli_lists "OpenCode itself names every server its global configuration declares" opencode mcp list \
    < <(fixture_servers "${GLOBAL_FIXTURES}/opencode.json" .mcp)
  assert_cli_lists "Kilo Code itself names every server its global configuration declares" kilocode mcp list \
    < <(fixture_servers "${GLOBAL_FIXTURES}/kilo.jsonc" .mcp)
  assert_cli_lists "Copilot itself names every server its user-scope file declares" copilot mcp list \
    < <(fixture_servers "${GLOBAL_FIXTURES}/copilot-mcp-config.json" .mcpServers)

  assert_archive_lacks "no project-scope server leaked into the global listings" "grafana"
}

# --- Spec 9, gate enforcement ------------------------------------------------

# Feeds one payload fixture to the gate copy in the home directory, from the
# bare working directory, and checks the decision it returns.
# Arguments: label, gate --format value, expected decision, payload file.
assert_gate() {
  local label="$1" format="$2" expect="$3" payload="$4"
  local output="" status=0 decision=""

  output="$(cd "$BARE" && python3 "$GATE" --format "$format" <"$payload" 2>&1)" || status=$?

  case "$format" in
    claude|codex)
      decision="$(jq -r '.hookSpecificOutput.permissionDecision // "allow"' <<<"${output:-null}" 2>/dev/null || echo "unparseable")"
      ;;
    plain)
      if [[ "$status" -eq 2 ]]; then decision="deny"; else decision="allow"; fi
      ;;
  esac

  if [[ "$decision" == "$expect" ]]; then
    pass "${label} (${format} decided ${decision})"
  else
    fail "${label} (${format} decided '${decision}', expected '${expect}')"
  fi
}

# Passes when the gate's refusal reason carries the needle, which is what tells
# rule A and rule B apart and names the subagent rule B refused.
assert_gate_reason() {
  local label="$1" format="$2" needle="$3" payload="$4"
  local output="" reason=""

  output="$(cd "$BARE" && python3 "$GATE" --format "$format" <"$payload" 2>&1)" || true
  reason="$(jq -r '.hookSpecificOutput.permissionDecisionReason // ""' <<<"${output:-null}" 2>/dev/null || echo "")"

  if [[ "$reason" == *"$needle"* ]]; then
    pass "${label}"
  else
    fail "${label} (the reason was '$(one_line "$reason")')"
  fi
}

verify_gate_enforcement() {
  section "Preflight gate enforcement from a bare directory"

  note "a live agent session needs provider credentials, so it is out of scope here."
  note "the gate copy in the home directory is driven with the payload each adapter would send it."

  assert_bare_working_directory "the working directory holds none of the per-project files"

  if [[ -e "${BARE}/.agents/hooks/preflight_gate.py" ]]; then
    fail "there is no project-relative gate script to fall back on (${BARE}/.agents/hooks/preflight_gate.py exists)"
  else
    pass "there is no project-relative gate script to fall back on"
  fi

  assert_gate "the home gate denies a main-thread source edit" claude deny \
    "${PAYLOADS}/main-thread-source-edit.json"
  assert_gate_reason "the refusal is rule A rather than rule B" claude "may not edit source files" \
    "${PAYLOADS}/main-thread-source-edit.json"
  assert_gate "the Codex adapter denies the same payload" codex deny \
    "${PAYLOADS}/main-thread-source-edit.json"
  assert_gate "the plain adapter denies by exiting 2" plain deny \
    "${PAYLOADS}/main-thread-source-edit.json"

  rm -f "$PROBE_AGENT"
  assert_gate "before the probe definition existed, the subagent payload was allowed" claude allow \
    "${PAYLOADS}/subagent-without-skills.json"

  cp "${FIXTURES}/${PROBE_NAME}.md" "$PROBE_AGENT"
  assert_gate "with the definition in the home directory, the same payload is denied" claude deny \
    "${PAYLOADS}/subagent-without-skills.json"
  assert_gate_reason "the refusal is rule B and names the probe" claude "$PROBE_NAME" \
    "${PAYLOADS}/subagent-without-skills.json"
  assert_gate "a subagent that declares skills is allowed from the same global directory" claude allow \
    "${PAYLOADS}/subagent-with-skills.json"

  rm -f "$PROBE_AGENT"
  assert_absent "the probe is gone again" ".claude/agents/${PROBE_NAME}.md"
}

# --- Scoped install ----------------------------------------------------------

# Echoes the paths the named agent owns, one per line.
agent_paths() {
  case "$1" in
    claude)   printf '%s\n' "${CLAUDE_PATHS[@]}" ;;
    codex)    printf '%s\n' "${CODEX_PATHS[@]}" ;;
    opencode) printf '%s\n' "${OPENCODE_PATHS[@]}" ;;
    kilo)     printf '%s\n' "${KILO_PATHS[@]}" ;;
    copilot)  printf '%s\n' "${COPILOT_PATHS[@]}" ;;
  esac
}

verify_scoped() {
  local agent="$1"
  local other="" path=""
  local paths=()

  section "Scoped install, ${agent} alone"

  note "the installer takes agent names, so this asserts it writes that agent's paths and no other's."

  assert_status "the scoped install exited 0" "$FIRST_INSTALL_STATUS" 0

  assert_glob_count "the shared skills tree landed, because every agent needs it" \
    ".agents/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_file "the gate script landed in the shared tree" ".agents/hooks/preflight_gate.py"
  assert_file_not_empty "the shared instruction file landed" ".agents/AGENTS.md"

  mapfile -t paths < <(agent_paths "$agent")
  for path in "${paths[@]}"; do
    assert_present "${agent} owns this path and it was written" "$path"
  done

  for other in claude codex opencode kilo copilot; do
    [[ "$other" == "$agent" ]] && continue

    mapfile -t paths < <(agent_paths "$other")
    for path in "${paths[@]}"; do
      assert_absent "${other} was not named, so nothing of its own was written" "$path"
    done
  done
}

# --- Reporting ---------------------------------------------------------------

summary() {
  section "Result"

  printf 'Passed: %d\n' "$PASSES"
  printf 'Failed: %d\n' "$FAILURES"

  if [[ "$FAILURES" -gt 0 ]]; then
    return 1
  fi
}

main() {
  parse_args "$@"
  collect_canonical
  reset_global

  if [[ -n "$SCOPED" ]]; then
    install_global "$SCOPED"
    verify_scoped "$SCOPED"
    summary
    return
  fi

  install_global
  verify_install_shape
  verify_agent_discovery
  verify_mcp_visibility
  verify_gate_enforcement
  summary
}

main "$@"
