#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: setup-global.sh
# Description: Installs or updates the shared configuration from the mounted
#              agent-standards repository in the container's own home directory,
#              the way docs/GLOBAL_SETUP.md describes a person doing it on their
#              machine: a temporary clone, ~/.agents as the one shared folder,
#              and nothing of the repository left behind afterwards.
#              Global counterpart of setup-project.sh.
# Usage: setup-global.sh [-h] [AGENT...]
#        setup-global.sh [-h] --update
# Agents: claude, codex, opencode, kilo, copilot. With none named, all five.
# Options:
#   -h, --help  Print this help and exit.
#   --update    Refresh only what is already installed, as the guide's
#               Updating section does. Takes no agent names.
# Environment:
#   AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
#   TMPDIR                Where the temporary clone is made. Default /tmp.
# Exit codes:
#   0  Every selected agent is installed, or the update ran, and nothing needs
#      a decision.
#   1  A step failed, or --update found nothing installed.
#   2  Bad arguments, or a required command is missing.
#   3  Installed, but one or more paths already existed and were left alone.
#      Nothing this script writes is ever deleted or overwritten in place.
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# --- Constants ---------------------------------------------------------------

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
readonly REPO="${AGENT_STANDARDS_REPO:-/repo}"
readonly KNOWN_AGENTS=(claude codex opencode kilo copilot)

readonly SHARED="${HOME}/.agents"
readonly SHARED_TREES=(skills agents hooks plugin)
readonly SHARED_SKILLS="${SHARED}/skills"
readonly SHARED_AGENTS="${SHARED}/agents"
readonly SHARED_PLUGIN="${SHARED}/plugin/hooks.js"
readonly SHARED_BIN="${SHARED}/bin"
readonly UPDATER="${SHARED_BIN}/update-global.sh"
readonly UPSTREAM_COMMIT="${SHARED}/.upstream-commit"
readonly INSTRUCTIONS="${HOME}/.claude/CLAUDE.md"
readonly GATE_SCRIPT="${SHARED}/hooks/preflight_gate.py"
readonly MARKER_SCRIPT="${SHARED}/hooks/no_ai_markers_check.py"
readonly TASKS_SCRIPT="${SHARED}/hooks/task_list_sync.py"
readonly PROMPT_SCRIPT="${SHARED}/hooks/copilot/prompt_reminder.py"

# --- State -------------------------------------------------------------------

SELECTED=()
UPDATE=0
MANUAL=0
EXIT_CODE=0
CLONE_PARENT=""
SRC=""

# --- Logging -----------------------------------------------------------------

log_step()  { echo "[STEP]  $*" >&2; }
log_info()  { echo "[INFO]  $*" >&2; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

trap 'log_error "${SCRIPT_NAME} failed at line ${LINENO}"' ERR

# Deletes the temporary clone however the script ends, so no copy of the
# repository is ever left in the container.
# shellcheck disable=SC2317,SC2329  # reached through the EXIT trap below
remove_clone() {
  if [[ -n "$CLONE_PARENT" && -d "$CLONE_PARENT" ]]; then
    rm -rf -- "$CLONE_PARENT"
  fi
}
trap remove_clone EXIT

usage() {
  cat <<'USAGE'
Usage: setup-global.sh [-h] [AGENT...]
       setup-global.sh [-h] --update

Installs the shared agent configuration from the mounted repository into the
container's home directory. Name the agents to install for, or name none and
get all five. With --update, refreshes only what is already installed.

Agents:
  claude      Claude Code       ~/.claude
  codex       Codex             ~/.codex
  opencode    OpenCode          ~/.config/opencode
  kilo        Kilo Code         ~/.config/kilo
  copilot     GitHub Copilot    ~/.copilot

Options:
  -h, --help  Print this help and exit.
  --update    Refresh what is installed, add nothing. Takes no agent names.

Environment:
  AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
  TMPDIR                Where the temporary clone is made. Default /tmp.

Exit codes:
  0  Installed or updated, nothing left to decide.
  1  A step failed, or --update found nothing installed.
  2  Bad arguments or a missing dependency.
  3  Installed, but a file already existed and was left alone.

Examples:
  setup-global.sh
  setup-global.sh codex
  setup-global.sh claude copilot
  setup-global.sh --update
USAGE
}

# --- Argument parsing --------------------------------------------------------

die_usage() {
  log_error "$1"
  echo >&2
  usage >&2
  exit 2
}

# Joins its arguments with a space, which "${array[*]}" cannot do here because
# the script sets IFS to newline and tab.
join_spaces() {
  local IFS=' '

  echo "$*"
}

is_known_agent() {
  local candidate="$1" known

  for known in "${KNOWN_AGENTS[@]}"; do
    [[ "$candidate" == "$known" ]] && return 0
  done

  return 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      --update)
        UPDATE=1
        shift
        ;;
      --)
        shift
        while [[ $# -gt 0 ]]; do
          SELECTED+=("$1")
          shift
        done
        ;;
      -*)
        die_usage "unknown option: $1"
        ;;
      *)
        SELECTED+=("$1")
        shift
        ;;
    esac
  done

  if [[ "$UPDATE" -eq 1 && "${#SELECTED[@]}" -gt 0 ]]; then
    die_usage "--update refreshes whatever is installed and takes no agent names"
  fi

  if [[ "${#SELECTED[@]}" -eq 0 ]]; then
    SELECTED=("${KNOWN_AGENTS[@]}")
  fi

  local agent
  for agent in "${SELECTED[@]}"; do
    if ! is_known_agent "$agent"; then
      die_usage "unknown agent: ${agent}. Known agents: $(join_spaces "${KNOWN_AGENTS[@]}")"
    fi
  done
}

# --- Preconditions -----------------------------------------------------------

require_tools() {
  if ! command -v git >/dev/null 2>&1; then
    log_error "git is required and was not found on PATH"
    exit 2
  fi
}

require_source_repo() {
  if [[ ! -d "${REPO}/.git" ]]; then
    log_error "no git repository at ${REPO}; mount the agent-standards checkout there"
    exit 2
  fi
}

# --- Filesystem helpers ------------------------------------------------------
#
# None of these deletes anything: a path that exists and is not what the install
# expects is reported and left exactly as it was.

needs_attention() {
  MANUAL=$((MANUAL + 1))
}

ensure_dir() {
  local directory="$1"

  if [[ -d "$directory" ]]; then
    return 0
  fi

  log_step "create directory ${directory}"
  mkdir -p "$directory"
}

# Copies the contents of a source tree over a destination tree, creating the
# destination first. Files the install owns are overwritten, anything else in
# the destination is left in place.
copy_tree() {
  local source="$1" destination="$2"

  log_step "copy ${source}/ into ${destination}/"

  if [[ ! -d "$source" ]]; then
    log_error "expected a directory at ${source}"
    return 1
  fi

  mkdir -p "$destination"
  cp -R "${source}/." "${destination}/"
}

copy_file() {
  local source="$1" destination="$2"

  log_step "copy ${source} to ${destination}"

  if [[ ! -f "$source" ]]; then
    log_error "expected a file at ${source}"
    return 1
  fi

  mkdir -p "$(dirname "$destination")"
  cp "$source" "$destination"
}

ensure_symlink() {
  local link="$1" target="$2"
  local current=""

  if [[ -L "$link" ]]; then
    current="$(readlink "$link")"

    if [[ "$current" == "$target" ]]; then
      log_info "${link} already points at ${target}"
      return 0
    fi

    log_warn "${link} points at ${current}, not at ${target}; left alone"
    needs_attention
    return 0
  fi

  if [[ -e "$link" ]]; then
    log_warn "${link} exists and is not a symlink; left alone, expected a link to ${target}"
    needs_attention
    return 0
  fi

  log_step "link ${link} to ${target}"
  mkdir -p "$(dirname "$link")"
  ln -s "$target" "$link"
}

# Writes a configuration file the install owns only when nothing is there yet.
# A file that already exists belongs to whoever put it there, so this never
# rewrites one. The marker is what makes a second run a no-op rather than a
# duplicate.
install_config() {
  local path="$1" marker="$2" content="$3"

  if [[ -e "$path" ]]; then
    if grep -qF -- "$marker" "$path"; then
      log_info "${path} already carries ${marker}"
      return 0
    fi

    log_warn "${path} exists and does not mention ${marker}; left alone"
    needs_attention
    return 0
  fi

  log_step "write ${path}"
  mkdir -p "$(dirname "$path")"
  printf '%s\n' "$content" >"$path"
}

# --- Step 1, the temporary clone ---------------------------------------------
#
# The guide clones GitHub into the temporary directory and deletes the clone
# when it is done. The one substitution here is the source: the mounted
# repository, so everything the install lands is the committed state of this
# checkout. The clone is removed by the EXIT trap, whatever happens.

ensure_safe_directory() {
  local directory="$1"

  if git config --global --get-all safe.directory 2>/dev/null | grep -qxF -- "$directory"; then
    return 0
  fi

  git config --global --add safe.directory "$directory"
}

clone_upstream() {
  ensure_safe_directory "$REPO"
  ensure_safe_directory "${REPO}/.git"

  CLONE_PARENT="$(mktemp -d)"
  SRC="${CLONE_PARENT}/agent-standards"

  log_step "clone ${REPO} into the temporary ${SRC}"
  git clone --quiet --filter=blob:none "file://${REPO}" "$SRC"
}

# --- Step 2, the one shared folder -------------------------------------------

record_upstream_commit() {
  log_step "record the installed commit in ${UPSTREAM_COMMIT}"
  git -C "$SRC" rev-parse HEAD >"$UPSTREAM_COMMIT"
}

install_shared_tree() {
  local tree

  log_info "installing the shared trees into ${SHARED}"

  ensure_dir "$SHARED"

  for tree in "${SHARED_TREES[@]}"; do
    copy_tree "${SRC}/.agents/${tree}" "${SHARED}/${tree}"
  done

  copy_tree "${SRC}/global/bin" "$SHARED_BIN"

  record_upstream_commit
}

# --- Step 3, the always-on instructions --------------------------------------

install_instructions() {
  ensure_dir "${HOME}/.claude"

  if [[ -e "$INSTRUCTIONS" ]]; then
    log_info "${INSTRUCTIONS} exists; left alone"
    return 0
  fi

  copy_file "${SRC}/AGENTS.md.example" "$INSTRUCTIONS"
}

# --- Per-agent configuration content -----------------------------------------
#
# Each of these prints the file the install writes when there is none. Every
# hook script is named by absolute path, because the wirings this repository
# ships call them as .agents/hooks/<name>.py, which resolves against the
# session's working directory and finds nothing outside an imported project.
#
# The event sets mirror the project wirings, minus the markdown lint pass. That
# one hook needs tools/check-markdown.py, which never leaves this repository, so
# wiring it globally would spawn an interpreter that returns 0 every time.

# shellcheck disable=SC2016  # the backticks are markdown in the reminder text, never command substitution
readonly PREFLIGHT_TEXT='PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default. Follow the user-communication skill when writing to the user. If the prompt asks anything, answer every question first, then start the work. End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:

Running: `running task name` (or: nothing)

~~DONE: older finished task~~
~~DONE: most recent finished task~~

**NOW: what is being done right now**

Next: the next task
Then: the task after that

Waiting on: what you wait for (or: nothing)

When several tasks run, list each name in backticks on the Running line, separated by commas.'

# Prints $1 with every newline replaced by $2, the escape a JSON string needs.
# Claude Code's command is one JSON string deep, Codex's JSON payload two deep.
escape_newlines() {
  local newline=$'\n'
  printf '%s' "${1//"$newline"/"$2"}"
}

PREFLIGHT_JSON="$(escape_newlines "$PREFLIGHT_TEXT" '\n')"
readonly PREFLIGHT_JSON
PREFLIGHT_NESTED_JSON="$(escape_newlines "$PREFLIGHT_TEXT" '\\n')"
readonly PREFLIGHT_NESTED_JSON

readonly SUPERVISION_TEXT="When you launch a background subagent, note how long its task should take and schedule a recurring check every 10 minutes while any subagent runs. At each check compare its running time and latest output with that expectation. Leave it alone unless it is far over (for example 30 minutes on a task that should take 1) or clearly looping, then ask it for status or stop it and tell the user why."

# The subagent text holds no newline, quote or backslash, so it goes into every
# JSON string as it is.
readonly SUBAGENT_TEXT='PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. Do the work yourself with your own tools and load the skills your definition names. The rules that the main thread must delegate and may not write files apply to the main thread only, so do not hand this task on and do not refuse it for that reason. The preflight gate still checks every tool call you make. Report back what you changed and how you verified it.'

# Prints a value escaped for the replacement side of a sed s#...#...# command,
# where a bare & names the match, # ends the command, and \ starts an escape.
sed_replacement() {
  printf '%s' "$1" | sed -e 's/[\\&#]/\\&/g'
}

claude_settings() {
  sed -e "s#@GATE@#$(sed_replacement "$GATE_SCRIPT")#g" -e "s#@MARKERS@#$(sed_replacement "$MARKER_SCRIPT")#g" -e "s#@TASKS@#$(sed_replacement "$TASKS_SCRIPT")#g" -e "s#@PREFLIGHT@#$(sed_replacement "$PREFLIGHT_JSON")#g" -e "s#@SUPERVISION@#$(sed_replacement "$SUPERVISION_TEXT")#g" -e "s#@SUBAGENT@#$(sed_replacement "$SUBAGENT_TEXT")#g" <<'JSON'
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '@PREFLIGHT@'"
          },
          {
            "type": "command",
            "command": "echo '@SUPERVISION@'"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event sessionstart --format claude ; exit 0"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '@PREFLIGHT@'"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"@SUBAGENT@\"}}'"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|WebFetch|WebSearch)$",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @GATE@ --format claude ; exit 0"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event precompact --format claude ; exit 0"
          }
        ]
      }
    ],
    "TaskCreated": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event taskcreated --format claude ; exit 0"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event taskcompleted --format claude ; exit 0"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @MARKERS@ --format claude --display-fixed ; exit 0"
          },
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event stop --format claude ; exit 0"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @MARKERS@ --format claude ; exit 0"
          }
        ]
      }
    ],
    "MessageDisplay": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @MARKERS@ --format claude --display ; exit 0"
          }
        ]
      }
    ]
  }
}
JSON
}

codex_hooks() {
  sed -e "s#@GATE@#$(sed_replacement "$GATE_SCRIPT")#g" -e "s#@MARKERS@#$(sed_replacement "$MARKER_SCRIPT")#g" -e "s#@TASKS@#$(sed_replacement "$TASKS_SCRIPT")#g" -e "s#@PREFLIGHT@#$(sed_replacement "$PREFLIGHT_NESTED_JSON")#g" -e "s#@SUBAGENT@#$(sed_replacement "$SUBAGENT_TEXT")#g" <<'JSON'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "grep -F '\"agent_id\"' >/dev/null || printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"@PREFLIGHT@\"}}'",
            "commandWindows": "if (-not [Console]::In.ReadToEnd().Contains(\"`\"agent_id`\"\")) { echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"@PREFLIGHT@\"}}' }; exit 0"
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "printf '%s\\n' '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"@SUBAGENT@\"}}'",
            "commandWindows": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"@SUBAGENT@\"}}'; exit 0"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Task list",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @TASKS@ --event sessionstart --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E @TASKS@ --event sessionstart --format codex 2>$null; exit 0"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Formatting check",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @MARKERS@ --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E @MARKERS@ --format codex 2>$null; exit 0"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "^(Bash|shell|apply_patch|Edit|Write|NotebookEdit)$",
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "timeout": 10,
            "command": "PY=$(command -v python3 || command -v python) && \"$PY\" -S -E @GATE@ --format codex 2>/dev/null || exit 0",
            "commandWindows": "$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E @GATE@ --format codex 2>$null; exit 0"
          }
        ]
      }
    ]
  }
}
JSON
}

# OpenCode names the shared plugin by absolute path, so an update of
# ~/.agents/plugin/hooks.js reaches it with nothing else to do.
opencode_config() {
  cat <<JSON
{
  "plugin": ["${SHARED_PLUGIN}"]
}
JSON
}

# Kilo Code reads no global AGENTS.md, so its instructions key points at the one
# instruction file, and it loads the same shared plugin as an absolute file URL.
kilo_config() {
  cat <<JSONC
{
  "instructions": ["${INSTRUCTIONS}"],
  "plugin": ["file://${SHARED_PLUGIN}"]
}
JSONC
}

# Copilot's hooks file is the one shipped in the repository with every hook call
# rewritten to an absolute path, so there is no second copy of its wording here.
# The bracket expressions keep the leading dot of the shipped relative path
# literal, so the match cannot slide onto a different directory.
copilot_hooks() {
  local shipped="${SRC}/.github/hooks/preflight.json"

  if [[ ! -f "$shipped" ]]; then
    log_error "expected a file at ${shipped}"
    return 1
  fi

  sed -e "s#[.]agents/hooks/preflight_gate[.]py#$(sed_replacement "$GATE_SCRIPT")#g" -e "s#[.]agents/hooks/task_list_sync[.]py#$(sed_replacement "$TASKS_SCRIPT")#g" -e "s#[.]agents/hooks/copilot/prompt_reminder[.]py#$(sed_replacement "$PROMPT_SCRIPT")#g" -e "s#[.]agents/hooks/no_ai_markers_check[.]py#$(sed_replacement "$MARKER_SCRIPT")#g" "$shipped"
}

# --- Per-agent installers ----------------------------------------------------

install_claude() {
  log_info "installing for Claude Code"

  ensure_symlink "${HOME}/.claude/skills" "$SHARED_SKILLS"
  copy_tree "${SRC}/.claude/agents" "${HOME}/.claude/agents"
  install_config "${HOME}/.claude/settings.json" "$GATE_SCRIPT" "$(claude_settings)"

  log_info "Claude Code stores user-scope MCP servers in ~/.claude.json; add them with claude mcp add --scope user"
}

install_codex() {
  log_info "installing for Codex"

  ensure_dir "${HOME}/.codex"
  copy_tree "${SRC}/.codex/agents" "${HOME}/.codex/agents"
  ensure_symlink "${HOME}/.codex/AGENTS.md" "$INSTRUCTIONS"
  install_config "${HOME}/.codex/hooks.json" "$GATE_SCRIPT" "$(codex_hooks)"
}

install_opencode() {
  log_info "installing for OpenCode"

  ensure_dir "${HOME}/.config/opencode"
  ensure_symlink "${HOME}/.config/opencode/agents" "$SHARED_AGENTS"
  install_config "${HOME}/.config/opencode/opencode.json" "$SHARED_PLUGIN" "$(opencode_config)"
}

install_kilo() {
  log_info "installing for Kilo Code"

  ensure_dir "${HOME}/.config/kilo"
  ensure_symlink "${HOME}/.config/kilo/agents" "$SHARED_AGENTS"
  install_config "${HOME}/.config/kilo/kilo.jsonc" "$SHARED_PLUGIN" "$(kilo_config)"
}

install_copilot() {
  log_info "installing for GitHub Copilot"

  ensure_dir "${HOME}/.copilot"
  copy_tree "${SRC}/.github/agents" "${HOME}/.copilot/agents"
  install_config "${HOME}/.copilot/hooks/preflight.json" "$GATE_SCRIPT" "$(copilot_hooks)"
  ensure_symlink "${HOME}/.copilot/copilot-instructions.md" "$INSTRUCTIONS"
}

install_agent() {
  case "$1" in
    claude)   install_claude ;;
    codex)    install_codex ;;
    opencode) install_opencode ;;
    kilo)     install_kilo ;;
    copilot)  install_copilot ;;
  esac
}

# --- Update ------------------------------------------------------------------
#
# The guide's Updating section is one command: the updater the install put in
# ~/.agents/bin. It is run here exactly as a person runs it, with the mounted
# repository as the URL it clones instead of GitHub, so the logic lives in that
# one script and is not repeated here.

update_installed() {
  if [[ ! -f "$UPSTREAM_COMMIT" ]]; then
    log_error "nothing to update: ${UPSTREAM_COMMIT} is missing, so no global install was found"
    exit 1
  fi

  if [[ ! -f "$UPDATER" ]]; then
    log_error "nothing to run: ${UPDATER} is missing, so the install predates the updater"
    exit 1
  fi

  ensure_safe_directory "$REPO"
  ensure_safe_directory "${REPO}/.git"

  log_step "run ${UPDATER} against file://${REPO}"
  sh "$UPDATER" --source "file://${REPO}"
}

# --- Reporting ---------------------------------------------------------------

announce_plan() {
  echo "==============================================================" >&2
  echo " agent-standards global install" >&2
  echo "==============================================================" >&2
  log_info "home directory: ${HOME}"
  log_info "install source: ${REPO}"

  if [[ "$UPDATE" -eq 1 ]]; then
    log_info "mode: update what is installed"
  else
    log_info "agents: $(join_spaces "${SELECTED[@]}")"
  fi

  echo "==============================================================" >&2
}

report_result() {
  echo "==============================================================" >&2

  if [[ "$UPDATE" -eq 1 ]]; then
    log_info "updated from $(<"$UPSTREAM_COMMIT")"
    return 0
  fi

  if [[ "$MANUAL" -gt 0 ]]; then
    log_warn "installed, with ${MANUAL} path(s) left alone because something was already there"
    EXIT_CODE=3
    return 0
  fi

  log_info "installed for: $(join_spaces "${SELECTED[@]}")"
}

# --- Entry point -------------------------------------------------------------

main() {
  parse_args "$@"
  require_tools
  require_source_repo
  announce_plan

  if [[ "$UPDATE" -eq 1 ]]; then
    update_installed
    report_result
    return 0
  fi

  clone_upstream
  install_shared_tree
  install_instructions

  local agent
  for agent in "${SELECTED[@]}"; do
    install_agent "$agent"
  done

  report_result
}

main "$@"
exit "$EXIT_CODE"
