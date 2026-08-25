#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: verify.sh
# Description: Asserts that every supported agent discovers the shared skills,
#              its own subagent tree, its preflight wiring and its MCP servers
#              in the imported throwaway project, and that the preflight gate
#              really denies what it claims to deny.
# Usage: verify.sh
# Environment:
#   HARNESS_PROJECT     Throwaway project directory. Default /work/project.
#   HARNESS_SKIP_SETUP  Set to 1 to assert against an existing project.
#   HARNESS_CLI_TIMEOUT Seconds allowed per agent CLI call. Default 300.
# Exit codes:
#   0  Every assertion passed.
#   1  At least one assertion failed.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

readonly PROJECT="${HARNESS_PROJECT:-/work/project}"
readonly SETUP="/harness/setup-project.sh"
readonly CLI_TIMEOUT="${HARNESS_CLI_TIMEOUT:-300}"
readonly GATE=".agents/hooks/preflight_gate.py"
readonly PROBE_AGENT=".claude/agents/harness-no-skills-probe.md"
readonly SAMPLE_SKILL="python-patterns"

PASSES=0
FAILURES=0
SKILL_COUNT=0

SUBAGENTS=()
MCP_SERVERS=()

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

assert_file() {
  local label="$1" path="$2"

  if [[ -f "${PROJECT}/${path}" ]]; then
    pass "${label} (${path})"
  else
    fail "${label} (${path} is missing)"
  fi
}

assert_absent() {
  local label="$1" path="$2"

  if [[ -e "${PROJECT}/${path}" ]]; then
    fail "${label} (${path} should not be here)"
  else
    pass "${label} (${path} stayed upstream)"
  fi
}

assert_symlinked_dir() {
  local label="$1" path="$2"

  if [[ -L "${PROJECT}/${path}" && -d "${PROJECT}/${path}" ]]; then
    pass "${label} (${path} points at $(readlink "${PROJECT}/${path}"))"
  else
    fail "${label} (${path} is not a symlink that resolves to a directory)"
  fi
}

assert_glob_count() {
  local label="$1" pattern="$2" expected="$3"
  local matches=()

  shopt -s nullglob
  # shellcheck disable=SC2206
  matches=( ${PROJECT}/${pattern} )
  shopt -u nullglob

  if [[ "${#matches[@]}" -eq "$expected" ]]; then
    pass "${label} (${#matches[@]} of ${expected})"
  else
    fail "${label} (found ${#matches[@]}, expected ${expected})"
  fi
}

assert_json() {
  local label="$1" path="$2" filter="$3"
  local result=""

  if [[ ! -f "${PROJECT}/${path}" ]]; then
    fail "${label} (${path} is missing)"
    return
  fi

  result="$(jq -r "$filter" "${PROJECT}/${path}" 2>/dev/null || echo "error")"

  if [[ "$result" == "true" ]]; then
    pass "${label}"
  else
    fail "${label} (the check over ${path} returned '${result}')"
  fi
}

# Same contract as assert_json, for a TOML file converted to JSON first so both
# schemas are checked with one query language.
assert_toml() {
  local label="$1" path="$2" filter="$3"
  local json="" result=""

  if ! json="$(python3 -c 'import json, sys, tomllib; json.dump(tomllib.load(open(sys.argv[1], "rb")), sys.stdout)' "${PROJECT}/${path}" 2>/dev/null)"; then
    fail "${label} (${path} is missing or does not parse as TOML)"
    return
  fi

  result="$(jq -r "$filter" <<<"$json" 2>/dev/null || echo "error")"

  if [[ "$result" == "true" ]]; then
    pass "${label}"
  else
    fail "${label} (the check over ${path} returned '${result}')"
  fi
}

# Runs an agent CLI inside the project and passes when every needle appears in
# its output. Needles arrive on stdin, one per line.
assert_cli_lists() {
  local label="$1"
  shift
  local needles=()
  local output="" status=0 missing=() needle=""

  mapfile -t needles < <(cat)

  output="$(cd "$PROJECT" && timeout "$CLI_TIMEOUT" "$@" </dev/null 2>&1)" || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "${label} (${1} exited ${status}: $(one_line "$output"))"
    return
  fi

  for needle in "${needles[@]}"; do
    if ! grep -qF -- "$needle" <<<"$output"; then
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
  local output="" status=0

  output="$(cd "$PROJECT" && timeout "$CLI_TIMEOUT" "$@" </dev/null 2>&1)" || status=$?

  if [[ "$status" -ne 0 ]]; then
    fail "${label} (${1} exited ${status}: $(one_line "$output"))"
    return
  fi

  if grep -qF -- "$needle" <<<"$output"; then
    fail "${label} (${1} reported: $(one_line "$(grep -m1 -A2 -F -- "$needle" <<<"$output")"))"
  else
    pass "${label}"
  fi
}

prepare_project() {
  if [[ "${HARNESS_SKIP_SETUP:-0}" == "1" ]]; then
    note "HARNESS_SKIP_SETUP=1, asserting against the existing ${PROJECT}"
  else
    "$SETUP"
  fi

  if [[ ! -d "$PROJECT" ]]; then
    printf 'FAIL  the throwaway project was not created at %s\n' "$PROJECT"
    exit 1
  fi

  mapfile -t SUBAGENTS < <(find "${PROJECT}/.agents/agents" -maxdepth 1 -name '*.md' -printf '%f\n' | sed 's/\.md$//' | sort)
  mapfile -t MCP_SERVERS < <(jq -r '.mcpServers | keys[]' "${PROJECT}/.mcp.json")
  SKILL_COUNT="$(cd "$PROJECT" && find .agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l)"
}

# Codex ignores the whole .codex/ layer until the project is trusted once. The
# trust record is written into the container HOME, never onto the host.
trust_project_for_codex() {
  mkdir -p "${HOME}/.codex"
  printf '[projects."%s"]\ntrust_level = "trusted"\n' "$PROJECT" > "${HOME}/.codex/config.toml"
}

verify_import() {
  section "Import, shared tree"

  assert_file "AGENTS.md was activated from the template" "AGENTS.md"
  assert_absent "the template was renamed rather than copied" "AGENTS.md.example"
  assert_absent "the canonical subagent source stays upstream" "subagents"
  assert_absent "the generator stays upstream" "tools"
  assert_file "the shared gate script landed" "$GATE"
  assert_file "the OpenCode and Kilo Code plugin landed" ".agents/plugin/hooks.js"
  assert_glob_count "every canonical skill landed" ".agents/skills/*/SKILL.md" "$SKILL_COUNT"
  assert_symlinked_dir "Claude Code skills symlink resolves" ".claude/skills"
  assert_symlinked_dir "OpenCode subagents symlink resolves" ".opencode/agents"
  assert_symlinked_dir "Kilo Code subagents symlink resolves" ".kilo/agents"
}

verify_claude() {
  section "Claude Code"

  assert_glob_count "skills are discoverable through the symlink Claude Code reads" \
    ".claude/skills/*/SKILL.md" "$SKILL_COUNT"
  assert_file "a known skill resolves through the symlink" \
    ".claude/skills/${SAMPLE_SKILL}/SKILL.md"
  assert_glob_count "subagents are discoverable in Claude Code format" \
    ".claude/agents/*.md" "${#SUBAGENTS[@]}"
  assert_json "the gate is wired into PreToolUse" ".claude/settings.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("preflight_gate.py --format claude"))'
  assert_json "the gate text is injected on every prompt" ".claude/settings.json" \
    '[.hooks.UserPromptSubmit[].hooks[].command] | any(contains("PREFLIGHT"))'
  assert_json "MCP servers are present in the file Claude Code reads" ".mcp.json" \
    '(.mcpServers | length) > 0'

  printf '%s\n' "${MCP_SERVERS[@]}" | assert_cli_lists \
    "Claude Code itself lists the project MCP servers" claude mcp list
}

verify_codex() {
  section "Codex"

  trust_project_for_codex

  assert_file "skills are discoverable in the directory Codex reads natively" \
    ".agents/skills/${SAMPLE_SKILL}/SKILL.md"
  assert_glob_count "subagents are discoverable in Codex TOML format" \
    ".codex/agents/*.toml" "${#SUBAGENTS[@]}"
  assert_toml "the gate is wired into PreToolUse" ".codex/config.toml" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("preflight_gate.py --format codex"))'
  assert_toml "the gate text is injected on every prompt" ".codex/config.toml" \
    '[.hooks.UserPromptSubmit[].hooks[].command] | any(contains("PREFLIGHT"))'
  assert_toml "MCP servers are present in the file Codex reads" ".codex/config.toml" \
    '(.mcp_servers | length) > 0'

  printf '%s\n' "${MCP_SERVERS[@]}" | assert_cli_lists \
    "Codex itself lists the project MCP servers" codex mcp list
}

verify_opencode() {
  section "OpenCode"

  assert_file "skills are discoverable in the directory OpenCode reads natively" \
    ".agents/skills/${SAMPLE_SKILL}/SKILL.md"
  assert_json "the gate plugin is declared by path" "opencode.json" \
    '[.plugin[]] | any(contains(".agents/plugin/hooks.js"))'
  assert_json "AGENTS.md is declared as the instruction file" "opencode.json" \
    '[.instructions[]] | any(. == "AGENTS.md")'
  assert_json "MCP servers are present in the file OpenCode reads" "opencode.json" \
    '(.mcp | length) > 0'

  printf '%s\n' "${SUBAGENTS[@]}" | assert_cli_lists \
    "OpenCode itself lists every imported subagent" opencode agent list
  printf '%s\n' "${MCP_SERVERS[@]}" | assert_cli_lists \
    "OpenCode itself lists the project MCP servers" opencode mcp list
}

verify_kilo() {
  section "Kilo Code"

  assert_file "skills are discoverable in the directory Kilo Code reads natively" \
    ".agents/skills/${SAMPLE_SKILL}/SKILL.md"
  assert_json "the gate plugin is declared in the file Kilo Code reads" "opencode.json" \
    '[.plugin[]] | any(contains(".agents/plugin/hooks.js"))'

  printf '%s\n' "${SUBAGENTS[@]}" | assert_cli_lists \
    "Kilo Code itself lists every imported subagent" kilocode agent list
  assert_cli_lacks "Kilo Code accepts opencode.json instead of rejecting it" \
    "Configuration is invalid" kilocode config check
  printf '%s\n' "${MCP_SERVERS[@]}" | assert_cli_lists \
    "Kilo Code itself lists the project MCP servers" kilocode mcp list
}

verify_copilot() {
  section "GitHub Copilot"

  assert_file "skills are discoverable in the directory Copilot reads natively" \
    ".agents/skills/${SAMPLE_SKILL}/SKILL.md"
  assert_glob_count "subagents are discoverable in Copilot agent format" \
    ".github/agents/*.agent.md" "${#SUBAGENTS[@]}"
  assert_json "the gate is wired into preToolUse" ".github/hooks/preflight.json" \
    '[.hooks.preToolUse[].command.bash] | any(contains("preflight_gate.py --format copilot"))'
  assert_json "the gate text is injected on session start" ".github/hooks/preflight.json" \
    '[.hooks.sessionStart[].command.bash] | any(contains("PREFLIGHT"))'
  assert_json "MCP servers are present in the file Copilot in VS Code reads" ".vscode/mcp.json" \
    '(.servers | length) > 0'

  printf '%s\n' "$SAMPLE_SKILL" "code-reviewer" "coding-standards" | assert_cli_lists \
    "Copilot itself lists the imported skills" copilot skill list
  assert_cli_lacks "every imported skill parses for Copilot" \
    "failed to load" copilot skill list
  printf '%s\n' "${MCP_SERVERS[@]}" | assert_cli_lists \
    "Copilot itself lists the project MCP servers" copilot mcp list
}

# Feeds one hook payload to the gate and checks the decision it returns.
# Arguments: label, gate --format value, expected decision, payload, optional
# extra flag such as --subagent.
assert_gate() {
  local label="$1" format="$2" expect="$3" payload="$4" extra="${5:-}"
  local args=("--format" "$format")
  local output="" status=0 decision=""

  if [[ -n "$extra" ]]; then
    args+=("$extra")
  fi

  output="$(cd "$PROJECT" && printf '%s' "$payload" | python3 "$GATE" "${args[@]}" 2>&1)" || status=$?

  case "$format" in
    claude|codex)
      decision="$(jq -r '.hookSpecificOutput.permissionDecision // "allow"' <<<"${output:-null}" 2>/dev/null || echo "unparseable")"
      ;;
    copilot)
      decision="$(jq -r '.permissionDecision // "allow"' <<<"${output:-null}" 2>/dev/null || echo "unparseable")"
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

write_probe_agent() {
  cat > "${PROJECT}/${PROBE_AGENT}" <<'AGENT'
---
name: harness-no-skills-probe
description: Fixture subagent that deliberately declares no skills.
---

Fixture used by the container harness to exercise rule B of the preflight gate.
AGENT
}

verify_gate_behaviour() {
  local format=""
  local main_source_edit='{"tool_name":"Edit","tool_input":{"file_path":"src/app.py"}}'
  local main_doc_edit='{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'
  local main_shell_write='{"tool_name":"Bash","tool_input":{"command":"echo x > src/app.py"}}'
  local specialist='{"agent_id":"a1","agent_type":"code-reviewer","tool_name":"Edit","tool_input":{"file_path":"src/app.py"}}'
  local generalist='{"agent_id":"a1","agent_type":"harness-no-skills-probe","tool_name":"Edit","tool_input":{"file_path":"src/app.py"}}'

  section "Preflight gate behaviour"

  note "a live agent session needs provider credentials, so it is out of scope here."
  note "the gate is driven directly with the payload each adapter would send it."

  for format in claude codex copilot plain; do
    assert_gate "rule A denies a main-thread source edit" "$format" deny "$main_source_edit"
  done

  assert_gate "a main-thread markdown edit is allowed" claude allow "$main_doc_edit"
  assert_gate "rule A denies a shell redirect into a source file" claude deny "$main_shell_write"
  assert_gate "a subagent that declares skills is allowed" claude allow "$specialist"

  write_probe_agent
  assert_gate "rule B denies a subagent that declares no skills" claude deny "$generalist"
  assert_gate "rule B reaches the OpenCode and Kilo Code adapter too" plain deny "$generalist" --subagent
  rm -f "${PROJECT}/${PROBE_AGENT}"

  assert_gate "a malformed payload fails open" claude allow 'not json at all'
}

summary() {
  section "Result"

  printf 'Passed: %d\n' "$PASSES"
  printf 'Failed: %d\n' "$FAILURES"

  if [[ "$FAILURES" -gt 0 ]]; then
    return 1
  fi
}

main() {
  prepare_project
  verify_import
  verify_claude
  verify_codex
  verify_opencode
  verify_kilo
  verify_copilot
  verify_gate_behaviour
  summary
}

main "$@"
