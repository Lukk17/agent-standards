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
readonly GUIDE="${REPO}/docs/GLOBAL_SETUP.md"
readonly INSTRUCTIONS="${HOME}/.claude/CLAUDE.md"
readonly SHARED_AGENTS="${HOME}/.agents/agents"
readonly SHARED_PLUGIN="${HOME}/.agents/plugin/hooks.js"
readonly OWN_SKILL="e2e-own-skill"

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
# ~/.claude/CLAUDE.md is on none of these lists: it is the one instruction file
# every agent reads, so step 3 of the guide writes it whichever agent is named.
readonly CLAUDE_PATHS=(".claude/skills" ".claude/agents" ".claude/settings.json")
readonly CODEX_PATHS=(".codex/agents" ".codex/AGENTS.md" ".codex/hooks.json")
readonly OPENCODE_PATHS=(".config/opencode/agents" ".config/opencode/opencode.json")
readonly KILO_PATHS=(".config/kilo/agents" ".config/kilo/kilo.jsonc")
readonly COPILOT_PATHS=(".copilot/agents" ".copilot/hooks" ".copilot/copilot-instructions.md")

# The temporary directory every installer run clones into. The guide leaves no
# copy of the repository behind, so it has to be empty after every run.
CLONE_TMP="$(mktemp -d -t sandbox-clone-XXXXXXXX)"
readonly CLONE_TMP

# The synthetic upstream the update spec releases from: a clone of the commit
# under test with further commits of its own, so the mounted repository is
# never written to.
UPSTREAM_TMP="$(mktemp -d -t sandbox-upstream-XXXXXXXX)"
readonly UPSTREAM_TMP
readonly UPSTREAM="${UPSTREAM_TMP}/agent-standards"

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
UPDATE_STATUS=0

cleanup() {
  local exit_code=$?

  rm -f "$CLI_OUTPUT" "$CLI_ARCHIVE"
  rm -rf "$CLONE_TMP" "$UPSTREAM_TMP"

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

# Passes when the path is a symlink whose target is exactly the given absolute
# path and resolves to something, which is how the guide makes every link.
assert_link_to() {
  local label="$1" path="$2" target="$3"
  local current=""

  if [[ ! -L "${HOME}/${path}" ]]; then
    fail "${label} (~/${path} is not a symlink)"
    return
  fi

  current="$(readlink "${HOME}/${path}")"

  if [[ "$current" == "$target" && -e "${HOME}/${path}" ]]; then
    pass "${label} (~/${path} points at ${target})"
  else
    fail "${label} (~/${path} points at '${current}', expected ${target} and a target that exists)"
  fi
}

# Passes when the file holds exactly the commit the repository is at, the
# mounted one unless a third argument names another.
assert_matches_head() {
  local label="$1" path="$2" repo="${3:-$REPO}"
  local head="" recorded=""

  head="$(git -C "$repo" rev-parse HEAD 2>/dev/null || echo "no HEAD")"
  recorded="$(cat "${HOME}/${path}" 2>/dev/null || echo "missing")"

  if [[ "$recorded" == "$head" ]]; then
    pass "${label} (${head})"
  else
    fail "${label} (~/${path} holds '${recorded}', HEAD is ${head})"
  fi
}

# Passes when the installed file is byte for byte the committed upstream file,
# in the mounted repository unless a fourth argument names another.
assert_matches_upstream() {
  local label="$1" path="$2" upstream="$3" repo="${4:-$REPO}"

  if git -C "$repo" show "HEAD:${upstream}" 2>/dev/null | cmp -s - "${HOME}/${path}"; then
    pass "${label} (~/${path} equals ${upstream} at HEAD)"
  else
    fail "${label} (~/${path} differs from ${upstream} at HEAD)"
  fi
}

# Passes when the installed JSON file equals the guide's block for it, with the
# guide's placeholder home directory read as the container's own. The block is
# the first json fence in docs/GLOBAL_SETUP.md that holds every marker.
assert_matches_guide() {
  local label="$1" path="$2"
  shift 2
  local result=""

  result="$(python3 - "$GUIDE" "${HOME}/${path}" "$HOME" "$@" <<'PY' 2>&1 || true
import json, re, sys

guide, installed, home, *markers = sys.argv[1:]
blocks = re.findall(r"^```json\n(.*?)^```$", open(guide, encoding="utf-8").read(), re.MULTILINE | re.DOTALL)
matching = [block for block in blocks if all(marker in block for marker in markers)]
if not matching:
    print("no json block in the guide holds " + ", ".join(markers))
    sys.exit(0)
expected = json.loads(matching[0].replace("/home/you/", home + "/"))
actual = json.load(open(installed, encoding="utf-8"))
print("same" if expected == actual else "differs")
PY
)"

  if [[ "$result" == "same" ]]; then
    pass "${label}"
  else
    fail "${label} ($(one_line "$result"))"
  fi
}

# Passes when the installer left nothing in the temporary directory it cloned
# into, so no copy of the repository outlives the run.
assert_clone_removed() {
  local label="$1"
  local leftovers=""

  leftovers="$(find "$CLONE_TMP" -mindepth 1 -maxdepth 1 -printf '%f ' 2>/dev/null)"

  if [[ -z "$leftovers" ]]; then
    pass "${label} (${CLONE_TMP} is empty)"
  else
    fail "${label} (${CLONE_TMP} still holds: ${leftovers})"
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

  note "the installer clones ${REPO} into ${CLONE_TMP} and writes into ${HOME}."

  TMPDIR="$CLONE_TMP" "$SETUP" "$@" || FIRST_INSTALL_STATUS=$?

  if [[ $# -eq 0 ]]; then
    TMPDIR="$CLONE_TMP" "$SETUP" || SECOND_INSTALL_STATUS=$?
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
  assert_status "the second install exited 0, so running a section again is safe" "$SECOND_INSTALL_STATUS" 0

  assert_bare_working_directory "the working directory holds none of the per-project files"

  assert_clone_removed "no temporary clone of the repository outlived the install"
  assert_absent "no permanent copy of the repository sits in the home directory" ".agent-standards"
  assert_matches_head "the shared folder records the commit under test as the one it was installed from" \
    ".agents/.upstream-commit"
  assert_absent "the shared folder holds no instruction file of its own" ".agents/AGENTS.md"

  assert_glob_count "the shared skills tree holds every canonical skill" \
    ".agents/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_link_to "Claude Code's skills location is a link to the shared skills" ".claude/skills" "${HOME}/.agents/skills"
  assert_glob_count "the same skill count is reachable through that symlink" \
    ".claude/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_file "the gate script landed in the shared tree" ".agents/hooks/preflight_gate.py"
  assert_file "the reply formatting check landed beside it" ".agents/hooks/no_ai_markers_check.py"
  assert_file "the task list hook landed beside it" ".agents/hooks/task_list_sync.py"
  assert_file "the markdown lint hook landed too, deliberately unwired" ".agents/hooks/markdown_lint_check.py"
  assert_matches_upstream "the POSIX updater landed in the shared folder" ".agents/bin/update-global.sh" \
    "global/bin/update-global.sh"
  assert_matches_upstream "the PowerShell updater landed beside it" ".agents/bin/update-global.ps1" \
    "global/bin/update-global.ps1"

  assert_glob_count "Claude Code has every subagent in its own markdown format" \
    ".claude/agents/*.md" "${#SUBAGENTS[@]}"
  assert_glob_count "Codex has every subagent in TOML" \
    ".codex/agents/*.toml" "${#SUBAGENTS[@]}"
  assert_glob_count "the shared OpenCode-format tree holds every subagent" \
    ".agents/agents/*.md" "${#SUBAGENTS[@]}"
  assert_link_to "OpenCode reads its subagents through a link to the shared tree" \
    ".config/opencode/agents" "$SHARED_AGENTS"
  assert_glob_count "OpenCode reaches every subagent through that link" \
    ".config/opencode/agents/*.md" "${#SUBAGENTS[@]}"
  assert_link_to "Kilo Code reads its subagents through a link to the same shared tree" \
    ".config/kilo/agents" "$SHARED_AGENTS"
  assert_glob_count "Kilo Code reaches every subagent through that link" \
    ".config/kilo/agents/*.md" "${#SUBAGENTS[@]}"
  assert_glob_count "GitHub Copilot has every subagent as *.agent.md" \
    ".copilot/agents/*.agent.md" "${#SUBAGENTS[@]}"

  assert_absent "the second install nested no tree inside the Claude Code one" ".claude/agents/agents"
  assert_absent "the second install nested no tree inside the shared one" ".agents/agents/agents"
  assert_absent "the second install nested no tree inside the shared skills" ".agents/skills/skills"

  assert_file_not_empty "there is one instruction file, ~/.claude/CLAUDE.md" ".claude/CLAUDE.md"
  assert_matches_upstream "it started from the template, because none existed" ".claude/CLAUDE.md" "AGENTS.md.example"
  assert_link_to "Codex points at it with a link" ".codex/AGENTS.md" "$INSTRUCTIONS"
  assert_absent "OpenCode gets no global rules file, so it falls back to ~/.claude/CLAUDE.md" \
    ".config/opencode/AGENTS.md"
  assert_link_to "Copilot points at it with a link of its own" ".copilot/copilot-instructions.md" "$INSTRUCTIONS"
  assert_json "Kilo Code points at it through its instructions key, by absolute path" ".config/kilo/kilo.jsonc" \
    ".instructions == [\"${INSTRUCTIONS}\"]"
  assert_json "Kilo Code needs no skills.paths entry, because it reads ~/.agents/skills natively" \
    ".config/kilo/kilo.jsonc" 'has("skills") | not'
  assert_json "Kilo Code names the shared plugin by absolute file URL" ".config/kilo/kilo.jsonc" \
    ".plugin == [\"file://${SHARED_PLUGIN}\"]"
  assert_json "OpenCode names the shared plugin by absolute path" ".config/opencode/opencode.json" \
    ".plugin == [\"${SHARED_PLUGIN}\"]"
  assert_matches_upstream "the shared plugin is the committed runner" ".agents/plugin/hooks.js" ".agents/plugin/hooks.js"
  assert_absent "OpenCode holds no copy of the plugin, which would load the runner twice" ".config/opencode/plugins"
  assert_absent "Kilo Code holds no copy of the plugin, which would load the runner twice" ".config/kilo/plugin"

  assert_matches_guide "Claude Code's user settings are the guide's block, with the home directory filled in" \
    ".claude/settings.json" '"MessageDisplay"' '"SubagentStart"'
  assert_matches_guide "Codex's user hooks are the guide's block, with the home directory filled in" \
    ".codex/hooks.json" '"commandWindows"' '"SubagentStart"'

  assert_json "Claude Code's user settings call the gate by absolute path" ".claude/settings.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py") and contains("--format claude"))'
  assert_json "Claude Code's user settings call the gate directly, force a zero exit, and the DEVNULL wrapper does not return" ".claude/settings.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("preflight_gate.py") and contains("--format claude") and endswith("; exit 0") and (contains("subprocess.DEVNULL") | not))'
  assert_json "Claude Code's user settings force a zero exit with a trailing ; exit 0" ".claude/settings.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(endswith("; exit 0"))'
  assert_json "Claude Code's user settings gate the web tools and the PowerShell tool as well as the writing ones" ".claude/settings.json" \
    '[.hooks.PreToolUse[].matcher] | any(type == "string" and test("Edit") and test("Write") and test("MultiEdit") and test("NotebookEdit") and test("Bash") and test("PowerShell") and test("WebFetch") and test("WebSearch"))'
  assert_json "Claude Code's user settings wire every event the project wiring wires but the markdown lint's" ".claude/settings.json" \
    '[.hooks | keys[]] == ["MessageDisplay", "PreCompact", "PreToolUse", "SessionStart", "Stop", "SubagentStart", "SubagentStop", "TaskCompleted", "TaskCreated", "UserPromptSubmit"]'
  assert_json "Claude Code's user settings tell a subagent to do its task itself, never hand it the delegating reminder" ".claude/settings.json" \
    '[.hooks.SubagentStart[].hooks[].command] | length > 0 and all(contains("PREFLIGHT for a subagent:") and (contains("Delegate investigation") | not))'
  assert_json "Claude Code's user settings inject the subagent supervision text at session start" ".claude/settings.json" \
    '[.hooks.SessionStart[].hooks[].command] | any(contains("When you launch a background subagent") and contains("every 10 minutes"))'
  assert_json "Claude Code's user settings leave the markdown lint out, because it needs a tool that never ships" ".claude/settings.json" \
    '[.hooks[][].hooks[].command] | any(contains("markdown_lint_check.py")) | not'
  assert_json "Claude Code's user settings check the reply formatting on both stop events" ".claude/settings.json" \
    '[[.hooks.Stop[].hooks[].command], [.hooks.SubagentStop[].hooks[].command] | map(select(contains("/.agents/hooks/no_ai_markers_check.py --format claude")))] | all(length == 1)'
  assert_json "Claude Code's user settings check what the display fix leaves on Stop and fix the reply on MessageDisplay" ".claude/settings.json" \
    '([.hooks.Stop[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format claude --display-fixed"))) and ([.hooks.MessageDisplay[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format claude --display ")))'
  assert_json "Claude Code's user settings mirror the task list on the five events that carry it" ".claude/settings.json" \
    '[.hooks.SessionStart[].hooks[].command, .hooks.PreCompact[].hooks[].command, .hooks.TaskCreated[].hooks[].command, .hooks.TaskCompleted[].hooks[].command, .hooks.Stop[].hooks[].command | select(contains("/.agents/hooks/task_list_sync.py")) | capture("--event (?<event>[a-z]+)").event] | sort == ["precompact", "sessionstart", "stop", "taskcompleted", "taskcreated"]'
  # shellcheck disable=SC2016  # the $ belongs to the hook command text the jq filter looks for
  assert_json "Claude Code's user settings resolve python3 first and fall back to python on every hook, calling the script by absolute path" ".claude/settings.json" \
    '[.hooks[][].hooks[].command | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))'
  assert_json "Codex's user hooks call the gate by absolute path" ".codex/hooks.json" \
    '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format codex"))'
  assert_json "Codex's user hooks scope the gate to the tools that can write" ".codex/hooks.json" \
    '[.hooks.PreToolUse[].matcher] | any(type == "string" and test("Bash") and test("apply_patch"))'
  assert_json "Codex's user hooks force a zero exit on the POSIX gate call, so a missing gate script allows rather than denies" ".codex/hooks.json" \
    '[.hooks.PreToolUse[].hooks[] | .command] | length > 0 and all(endswith("|| exit 0"))'
  assert_json "Codex's user hooks force a zero exit on every Windows command with a trailing ; exit 0, the PowerShell form" ".codex/hooks.json" \
    '[.hooks[][].hooks[] | (.commandWindows // empty)] | length > 0 and all(endswith("; exit 0"))'
  assert_json "Codex's user hooks tell a subagent to do its task itself, never hand it the delegating reminder" ".codex/hooks.json" \
    '[.hooks.SubagentStart[].hooks[].command] | length > 0 and all(contains("PREFLIGHT for a subagent:") and (contains("Delegate investigation") | not))'
  assert_json "Codex's user hooks wire the same five events the project configuration wires" ".codex/hooks.json" \
    '[.hooks | keys[]] == ["PreToolUse", "SessionStart", "Stop", "SubagentStart", "UserPromptSubmit"]'
  assert_json "Codex's user hooks check the reply formatting on Stop, by absolute path" ".codex/hooks.json" \
    '[.hooks.Stop[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format codex"))'
  assert_json "Codex's user hooks put the task list back at the start of a session, by absolute path" ".codex/hooks.json" \
    '[.hooks.SessionStart[].hooks[].command] | any(contains("/.agents/hooks/task_list_sync.py --event sessionstart --format codex"))'
  # shellcheck disable=SC2016  # the $ belongs to the hook command text the jq filter looks for
  assert_json "Codex's user hooks resolve python3 first and fall back to python on every POSIX command, calling the script by absolute path" ".codex/hooks.json" \
    '[.hooks[][].hooks[] | (.command // empty) | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))'
  # shellcheck disable=SC2016  # the $ belongs to the hook command text the jq filter looks for
  assert_json "Codex's user hooks move every Windows script call to the project root in PowerShell and leave it on python, the only name a python.org install puts on the path" ".codex/hooks.json" \
    '[.hooks[][].hooks[] | (.commandWindows // empty) | select(contains(".py"))] | length > 0 and all(startswith("$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /"))'
  assert_json "Codex's user hooks carry the canonical gate wording on the main-thread event, not a shortened copy" ".codex/hooks.json" \
    '[.hooks.UserPromptSubmit[].hooks[].command] | length >= 1 and all(contains("Delegate investigation, review and bounded implementation by default."))'
  assert_json "Codex's user hooks give every command a Windows sibling, because Codex picks one per platform" ".codex/hooks.json" \
    '[.hooks[][].hooks[] | select(has("command"))] | length > 0 and all(has("commandWindows"))'
  assert_json "Copilot's user hooks call the gate by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks.preToolUse[].bash] | any(contains("/.agents/hooks/preflight_gate.py --format copilot"))'
  assert_json "Copilot's user hooks put the task list back at the start of a session, by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks.sessionStart[].bash] | any(contains("/.agents/hooks/task_list_sync.py --event sessionstart --format copilot"))'
  assert_json "Copilot's user hooks append the reminder to every prompt, by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks.userPromptTransformed[].bash] | any(contains("/.agents/hooks/copilot/prompt_reminder.py"))'
  assert_json "Copilot's user hooks check the reply formatting on agentStop, by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks.agentStop[].bash] | any(contains("/.agents/hooks/no_ai_markers_check.py --format copilot"))'
  # shellcheck disable=SC2016  # the $ belongs to the hook command text the jq filter looks for
  assert_json "Copilot's user hooks resolve python3 first and fall back to python on every bash command, calling the script by absolute path" ".copilot/hooks/preflight.json" \
    '[.hooks[][] | (.bash // empty) | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))'
  assert_json "Copilot's user hooks leave every PowerShell command on python, the only name a python.org install puts on the path" ".copilot/hooks/preflight.json" \
    '[.hooks[][] | (.powershell // empty) | select(contains(".py"))] | length > 0 and all(startswith("python -S -E /"))'
  assert_file_lacks "no project-relative hook call survived the rewrite" \
    ".copilot/hooks/preflight.json" "-E .agents/hooks/"
}

# --- Spec 6, the update ------------------------------------------------------

# Digest of a file under the home directory, "missing" when it is not there.
home_digest() {
  sha256sum "${HOME}/$1" 2>/dev/null | cut -d' ' -f1 || echo "missing"
}

# One digest over every file the install writes, so a dry run that wrote
# anything at all shows up as a different value.
home_tree_digest() {
  (cd "$HOME" && find .agents .claude .codex .copilot .config -type f -print 2>/dev/null | sort | xargs -d '\n' sha256sum) \
    | sha256sum | cut -d' ' -f1 || true
}

# Runs git in the synthetic upstream with a throwaway identity for its commits.
upstream_git() {
  git -C "$UPSTREAM" -c user.name=e2e -c user.email=e2e@example.invalid "$@"
}

# Passes when the captured updater output holds the exact line.
assert_output_line() {
  local label="$1" line="$2"

  if grep -qxF -- "$line" "$CLI_OUTPUT"; then
    pass "${label} (${line})"
  else
    fail "${label} (no line '${line}' in: $(one_line_capture))"
  fi
}

# Builds the second release: a clone of the commit under test with one commit
# on top that changes, adds and removes files in every tree the updater reads,
# ships a skill the user never installed, and changes the Claude Code wiring.
release_synthetic_upstream() {
  local kept_skill="$1" removed_skill="$2" reference="$3"

  git clone --quiet "file://${REPO}" "$UPSTREAM"

  printf '\n# e2e second release\n' >>"${UPSTREAM}/.agents/hooks/preflight_gate.py"
  printf 'pass\n' >"${UPSTREAM}/.agents/hooks/e2e_added_hook.py"
  upstream_git rm --quiet .agents/hooks/markdown_lint_check.py "$reference"
  printf 'e2e reference\n' >"${UPSTREAM}/.agents/skills/${kept_skill}/e2e-added.md"
  printf '\ne2e second release\n' >>"${UPSTREAM}/.agents/skills/${kept_skill}/SKILL.md"
  printf '\ne2e second release\n' >>"${UPSTREAM}/.agents/skills/${removed_skill}/SKILL.md"
  mkdir -p "${UPSTREAM}/.agents/skills/e2e-new-skill"
  printf -- '---\nname: e2e-new-skill\ndescription: Shipped upstream, never installed.\n---\n' \
    >"${UPSTREAM}/.agents/skills/e2e-new-skill/SKILL.md"
  printf '\ne2e second release\n' >>"${UPSTREAM}/.agents/agents/${SUBAGENTS[0]}.md"
  printf '\ne2e second release\n' >>"${UPSTREAM}/.claude/agents/${SUBAGENTS[0]}.md"
  printf '\n' >>"${UPSTREAM}/.claude/settings.json"

  upstream_git add --all
  upstream_git commit --quiet -m "e2e second release"
}

verify_update() {
  local removed_skill="${SKILLS[-1]}" removed_agent="${SUBAGENTS[-1]}"
  local kept_skill="" reference="" settings_before="" own_before="" tree_before="" status=0

  section "Update, refreshing only what is installed"

  reference="$(git -C "$REPO" ls-tree -r --name-only HEAD -- .agents/skills | awk -v skip="/${removed_skill}/" \
    '!found && /^\.agents\/skills\/[^\/]+\/references\/[^\/]+\.md$/ && index($0, skip) == 0 { print; found = 1 }')"
  kept_skill="$(printf '%s' "$reference" | cut -d/ -f3)"

  note "the user deletes ${removed_skill} and ${removed_agent}, adds ${OWN_SKILL} and damages three installed files."
  note "the second release changes, adds and removes files across hooks, ${kept_skill} and the subagents."

  rm -rf "${HOME}/.agents/skills/${removed_skill}"
  rm -f "${HOME}/.claude/agents/${removed_agent}.md"
  mkdir -p "${HOME}/.agents/skills/${OWN_SKILL}"
  printf -- '---\nname: %s\ndescription: A skill of the user own.\n---\n' "$OWN_SKILL" \
    >"${HOME}/.agents/skills/${OWN_SKILL}/SKILL.md"
  printf '\n# damaged\n' >>"${HOME}/.agents/hooks/preflight_gate.py"
  printf '\ndamaged\n' >>"${HOME}/.agents/skills/${kept_skill}/SKILL.md"
  printf '\ndamaged\n' >>"${HOME}/.agents/agents/${SUBAGENTS[0]}.md"

  release_synthetic_upstream "$kept_skill" "$removed_skill" "$reference"

  settings_before="$(home_digest .claude/settings.json)"
  own_before="$(home_digest ".agents/skills/${OWN_SKILL}/SKILL.md")"
  tree_before="$(home_tree_digest)"

  TMPDIR="$CLONE_TMP" sh "${HOME}/.agents/bin/update-global.sh" --dry-run --source "file://${UPSTREAM}" \
    >"$CLI_OUTPUT" 2>&1 || status=$?

  assert_status "the dry run exited 0" "$status" 0
  if [[ "$(home_tree_digest)" == "$tree_before" ]]; then
    pass "the dry run wrote nothing under the home directory"
  else
    fail "the dry run changed files under the home directory"
  fi
  assert_output_line "the dry run lists an added hook" "add     ~/.agents/hooks/e2e_added_hook.py"
  assert_output_line "the dry run lists a hook removed upstream" "remove  ~/.agents/hooks/markdown_lint_check.py"
  assert_clone_removed "no temporary clone of the repository outlived the dry run"

  AGENT_STANDARDS_REPO="$UPSTREAM" TMPDIR="$CLONE_TMP" "$SETUP" --update >"$CLI_OUTPUT" 2>&1 || UPDATE_STATUS=$?

  assert_status "the update exited 0" "$UPDATE_STATUS" 0
  assert_clone_removed "no temporary clone of the repository outlived the update"
  assert_matches_upstream "the update refreshed a changed hook" ".agents/hooks/preflight_gate.py" \
    ".agents/hooks/preflight_gate.py" "$UPSTREAM"
  assert_matches_upstream "the update added a hook upstream added" ".agents/hooks/e2e_added_hook.py" \
    ".agents/hooks/e2e_added_hook.py" "$UPSTREAM"
  assert_absent "the update removed a hook upstream removed" ".agents/hooks/markdown_lint_check.py"
  assert_matches_upstream "the update kept the updater itself current" ".agents/bin/update-global.sh" \
    "global/bin/update-global.sh" "$UPSTREAM"
  assert_matches_upstream "the update refreshed an installed skill" ".agents/skills/${kept_skill}/SKILL.md" \
    ".agents/skills/${kept_skill}/SKILL.md" "$UPSTREAM"
  assert_matches_upstream "the update added a file upstream added to an installed skill" \
    ".agents/skills/${kept_skill}/e2e-added.md" ".agents/skills/${kept_skill}/e2e-added.md" \
    "$UPSTREAM"
  assert_absent "the update removed a file upstream removed from an installed skill" "$reference"
  assert_matches_upstream "the update refreshed an installed subagent in the shared tree" \
    ".agents/agents/${SUBAGENTS[0]}.md" ".agents/agents/${SUBAGENTS[0]}.md" "$UPSTREAM"
  assert_matches_upstream "the update refreshed an installed Claude Code subagent" \
    ".claude/agents/${SUBAGENTS[0]}.md" ".claude/agents/${SUBAGENTS[0]}.md" "$UPSTREAM"
  assert_absent "the update did not bring back a skill the user deleted" ".agents/skills/${removed_skill}"
  assert_absent "the update did not bring back a subagent the user deleted" ".claude/agents/${removed_agent}.md"
  assert_absent "the update did not add a skill the user never installed" ".agents/skills/e2e-new-skill"
  assert_output_line "the update named the Claude Code wiring as changed upstream" "  .claude/settings.json"

  if [[ "$(home_digest ".agents/skills/${OWN_SKILL}/SKILL.md")" == "$own_before" ]]; then
    pass "the update left the user's own skill alone"
  else
    fail "the update changed the user's own skill ~/.agents/skills/${OWN_SKILL}"
  fi

  if [[ "$(home_digest .claude/settings.json)" == "$settings_before" ]]; then
    pass "the update did not touch ~/.claude/settings.json, which holds the user's own settings"
  else
    fail "the update rewrote ~/.claude/settings.json"
  fi

  assert_matches_head "the update recorded the commit it refreshed from" ".agents/.upstream-commit" "$UPSTREAM"

  note "a third release reverts the second, so the home is back on the commit under test for the later specs."

  upstream_git revert --no-edit HEAD >/dev/null
  status=0
  AGENT_STANDARDS_REPO="$UPSTREAM" TMPDIR="$CLONE_TMP" "$SETUP" --update >"$CLI_OUTPUT" 2>&1 || status=$?

  assert_status "the reverting update exited 0" "$status" 0
  assert_absent "the reverting update removed the hook the second release added" ".agents/hooks/e2e_added_hook.py"
  assert_matches_upstream "the reverting update brought the removed hook back" \
    ".agents/hooks/markdown_lint_check.py" ".agents/hooks/markdown_lint_check.py"
  assert_matches_upstream "the reverting update restored the changed hook" ".agents/hooks/preflight_gate.py" \
    ".agents/hooks/preflight_gate.py"
  assert_matches_upstream "the reverting update brought the removed skill file back" "$reference" "$reference"
  assert_absent "the reverting update removed the skill file the second release added" \
    ".agents/skills/${kept_skill}/e2e-added.md"

  note "the guide's way to add a skill back is to copy its one folder; the same is done here from ${REPO}."

  rm -rf "${HOME}/.agents/skills/${OWN_SKILL}"
  cp -R "${REPO}/.agents/skills/${removed_skill}" "${HOME}/.agents/skills/${removed_skill}"
  cp "${REPO}/.claude/agents/${removed_agent}.md" "${HOME}/.claude/agents/${removed_agent}.md"
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

# Merges a fixture's keys into a configuration file the installer wrote, the
# way the guide says to merge a block rather than overwrite a file, so the
# plugin and instructions entries survive next to the MCP servers.
merge_json_fixture() {
  local fixture="$1" target="$2"
  local merged=""

  merged="$(jq -s '.[0] * .[1]' "$target" "$fixture")"
  printf '%s\n' "$merged" >"$target"
}

install_user_scope_mcp() {
  note "the installer writes no MCP configuration, deliberately, so the fixtures place every server here."

  cp "${GLOBAL_FIXTURES}/codex-config.toml" "${HOME}/.codex/config.toml"
  merge_json_fixture "${GLOBAL_FIXTURES}/opencode.json" "${HOME}/.config/opencode/opencode.json"
  merge_json_fixture "${GLOBAL_FIXTURES}/kilo.jsonc" "${HOME}/.config/kilo/kilo.jsonc"
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

# Writes one main-thread edit payload naming the target it wants to write and
# the project root the agent has open, the way every adapter sends its cwd.
gate_payload() {
  local target="$1" project="$2"

  jq -n --arg target "$target" --arg project "$project" \
    '{tool_name: "Edit", tool_input: {file_path: $target}, cwd: $project}'
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
  assert_gate_reason "the refusal is rule A rather than rule B" claude "may not write files directly" \
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

  note "the gate lives under the home directory here, so the home directory is not itself a protected project."

  local project="" notes=""
  project="$(mktemp -d "${HOME}/e2e-gate-project.XXXXXX")"
  notes="${HOME}/e2e-gate-notes"
  mkdir -p "$notes"

  gate_payload "${notes}/MEMORY.md" "$project" >"${project}/allow.json"
  gate_payload "${project}/src/app.py" "$project" >"${project}/deny.json"

  assert_gate "a write elsewhere under the home directory is outside the open project" claude allow \
    "${project}/allow.json"
  assert_gate "a write inside the project the payload names is denied" claude deny \
    "${project}/deny.json"

  rm -rf "$project" "$notes"

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

  assert_clone_removed "no temporary clone of the repository outlived the install"
  assert_glob_count "the shared skills tree landed, because every agent needs it" \
    ".agents/skills/*/SKILL.md" "$SKILL_FILE_COUNT"
  assert_glob_count "the shared subagent tree landed, because step 2 copies all four shared trees" \
    ".agents/agents/*.md" "${#SUBAGENTS[@]}"
  assert_file "the gate script landed in the shared tree" ".agents/hooks/preflight_gate.py"
  assert_file "the plugin landed in the shared tree" ".agents/plugin/hooks.js"
  assert_matches_head "the shared folder records the commit it was installed from" ".agents/.upstream-commit"
  assert_file_not_empty "the one instruction file landed, because step 3 is shared" ".claude/CLAUDE.md"

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
  verify_update
  verify_agent_discovery
  verify_mcp_visibility
  verify_gate_enforcement
  summary
}

main "$@"
