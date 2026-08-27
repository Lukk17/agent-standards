#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: setup-global.sh
# Description: Installs the shared configuration from the mounted agent-standards
#              repository into the container's own home directory, the way
#              docs/GLOBAL_SETUP.md describes a person doing it on their machine.
#              Global counterpart of setup-project.sh.
# Usage: setup-global.sh [-h] [AGENT...]
# Agents: claude, codex, opencode, kilo, copilot. With none named, all five.
# Options:
#   -h, --help  Print this help and exit.
# Environment:
#   AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
#   SANDBOX_CHECKOUT      Shared checkout the install copies from.
#                         Default $HOME/.agent-standards.
# Exit codes:
#   0  Every selected agent is installed and nothing needs a decision.
#   1  A step failed.
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
readonly CHECKOUT="${SANDBOX_CHECKOUT:-${HOME}/.agent-standards}"
readonly KNOWN_AGENTS=(claude codex opencode kilo copilot)

# Cone-mode sparse checkout also brings every file in the repository root, which
# is how AGENTS.md.example arrives.
readonly SPARSE_DIRS=(.agents .claude .codex .github .kilo .opencode docs)

readonly SHARED="${HOME}/.agents"
readonly SHARED_SKILLS="${SHARED}/skills"
readonly SHARED_AGENTS="${SHARED}/agents"
readonly SHARED_PLUGIN="${SHARED}/plugin/hooks.js"
readonly SHARED_INSTRUCTIONS="${SHARED}/AGENTS.md"
readonly GATE_SCRIPT="${SHARED}/hooks/preflight_gate.py"
readonly MARKER_SCRIPT="${SHARED}/hooks/no_ai_markers_check.py"

# --- State -------------------------------------------------------------------

SELECTED=()
MANUAL=0
EXIT_CODE=0

# --- Logging -----------------------------------------------------------------

log_step()  { echo "[STEP]  $*" >&2; }
log_info()  { echo "[INFO]  $*" >&2; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

trap 'log_error "${SCRIPT_NAME} failed at line ${LINENO}"' ERR

usage() {
  cat <<'USAGE'
Usage: setup-global.sh [-h] [AGENT...]

Installs the shared agent configuration from the mounted repository into the
container's home directory. Name the agents to install for, or name none and
get all five.

Agents:
  claude      Claude Code       ~/.claude
  codex       Codex             ~/.codex
  opencode    OpenCode          ~/.config/opencode
  kilo        Kilo Code         ~/.config/kilo
  copilot     GitHub Copilot    ~/.copilot

Options:
  -h, --help  Print this help and exit.

Environment:
  AGENT_STANDARDS_REPO  Mounted upstream repository. Default /repo.
  SANDBOX_CHECKOUT      Shared checkout the install copies from.
                        Default $HOME/.agent-standards.

Exit codes:
  0  Installed, nothing left to decide.
  1  A step failed.
  2  Bad arguments or a missing dependency.
  3  Installed, but a file already existed and was left alone.

Examples:
  setup-global.sh
  setup-global.sh codex
  setup-global.sh claude copilot
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

# True when the file ends in a newline, or does not exist yet.
ends_with_newline() {
  local file="$1"

  [[ -s "$file" ]] || return 0
  [[ -z "$(tail -c 1 "$file")" ]]
}

ensure_line() {
  local file="$1" line="$2"

  if [[ -f "$file" ]] && grep -qxF -- "$line" "$file"; then
    log_info "${file} already carries the line ${line}"
    return 0
  fi

  log_step "append the line ${line} to ${file}"
  mkdir -p "$(dirname "$file")"

  if ! ends_with_newline "$file"; then
    printf '\n' >>"$file"
  fi

  printf '%s\n' "$line" >>"$file"
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

# --- The shared checkout -----------------------------------------------------
#
# The install copies from a clone of the mounted repository rather than from the
# mount itself, so everything it lands is committed state. This mirrors
# setup-project.sh, which fetches the same committed state through a remote.

update_checkout() {
  log_step "refresh the sparse checkout at ${CHECKOUT}"

  git -C "$CHECKOUT" sparse-checkout set "${SPARSE_DIRS[@]}"

  if ! git -C "$CHECKOUT" pull --ff-only --quiet; then
    log_warn "could not fast-forward ${CHECKOUT}; installing from the commit already there"
  fi
}

create_checkout() {
  log_step "clone ${REPO} into ${CHECKOUT}"

  git clone --quiet --sparse "$REPO" "$CHECKOUT"
  git -C "$CHECKOUT" sparse-checkout set "${SPARSE_DIRS[@]}"
  git -C "$CHECKOUT" remote set-url --push origin no_push
}

ensure_checkout() {
  git config --global --add safe.directory "$REPO"
  git config --global --add safe.directory "${REPO}/.git"
  git config --global --add safe.directory "$CHECKOUT"

  if [[ -d "${CHECKOUT}/.git" ]]; then
    update_checkout
    return 0
  fi

  if [[ -e "$CHECKOUT" ]]; then
    log_error "${CHECKOUT} exists and is not a git checkout"
    exit 1
  fi

  create_checkout
}

# --- Shared tree, read by Codex, OpenCode and GitHub Copilot as it stands -----

install_shared_tree() {
  log_info "installing the shared tree into ${SHARED}"

  ensure_dir "$SHARED"
  copy_tree "${CHECKOUT}/.agents" "$SHARED"

  if [[ -e "$SHARED_INSTRUCTIONS" ]]; then
    log_info "${SHARED_INSTRUCTIONS} exists; left alone"
    return 0
  fi

  copy_file "${CHECKOUT}/AGENTS.md.example" "$SHARED_INSTRUCTIONS"
}

# --- Per-agent configuration content -----------------------------------------
#
# Each of these prints the file the install writes when there is none. The gate
# is named by absolute path, because every wiring this repository ships calls it
# as .agents/hooks/preflight_gate.py, which resolves against the session's
# working directory and finds nothing outside an imported project.

readonly PREFLIGHT_TEXT="PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default."

claude_settings() {
  sed -e "s#@GATE@#${GATE_SCRIPT}#g" -e "s#@MARKERS@#${MARKER_SCRIPT}#g" -e "s#@PREFLIGHT@#${PREFLIGHT_TEXT}#g" <<'JSON'
{
  "hooks": {
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
    "PreToolUse": [
      {
        "matcher": "^(Edit|Write|NotebookEdit|Bash)$",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "python @GATE@ --format claude ; exit 0"
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
            "command": "python @MARKERS@ ; exit 0"
          }
        ]
      }
    ]
  }
}
JSON
}

codex_hooks() {
  sed -e "s#@GATE@#${GATE_SCRIPT}#g" -e "s#@PREFLIGHT@#${PREFLIGHT_TEXT}#g" <<'JSON'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"@PREFLIGHT@\"}}'",
            "commandWindows": "echo {\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"@PREFLIGHT@\"}}"
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
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"@PREFLIGHT@\"}}'",
            "commandWindows": "echo {\"hookSpecificOutput\": {\"hookEventName\": \"SubagentStart\", \"additionalContext\": \"@PREFLIGHT@\"}}"
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
            "command": "python @GATE@ --format codex 2>/dev/null || exit 0",
            "commandWindows": "python @GATE@ --format codex 2>nul || exit 0"
          }
        ]
      }
    ]
  }
}
JSON
}

kilo_config() {
  cat <<'JSONC'
{
  "skills": {
    "paths": ["~/.agents/skills"]
  },
  "instructions": ["~/.agents/AGENTS.md"]
}
JSONC
}

# Copilot's hooks file is the one shipped in the repository with the gate call
# rewritten to an absolute path, so there is no second copy of its wording here.
copilot_hooks() {
  local shipped="${CHECKOUT}/.github/hooks/preflight.json"

  if [[ ! -f "$shipped" ]]; then
    log_error "expected a file at ${shipped}"
    return 1
  fi

  sed -e "s#python .agents/hooks/preflight_gate.py#python ${GATE_SCRIPT}#g" "$shipped"
}

# --- Per-agent installers ----------------------------------------------------

install_claude() {
  log_info "installing for Claude Code"

  ensure_dir "${HOME}/.claude"
  ensure_symlink "${HOME}/.claude/skills" "$SHARED_SKILLS"
  copy_tree "${CHECKOUT}/.claude/agents" "${HOME}/.claude/agents"
  ensure_line "${HOME}/.claude/CLAUDE.md" "@~/.agents/AGENTS.md"
  install_config "${HOME}/.claude/settings.json" "$GATE_SCRIPT" "$(claude_settings)"

  log_info "Claude Code stores user-scope MCP servers in ~/.claude.json; add them with claude mcp add --scope user"
}

install_codex() {
  log_info "installing for Codex"

  ensure_dir "${HOME}/.codex"
  copy_tree "${CHECKOUT}/.codex/agents" "${HOME}/.codex/agents"
  ensure_symlink "${HOME}/.codex/AGENTS.md" "$SHARED_INSTRUCTIONS"
  install_config "${HOME}/.codex/hooks.json" "$GATE_SCRIPT" "$(codex_hooks)"
}

install_opencode() {
  log_info "installing for OpenCode"

  ensure_dir "${HOME}/.config/opencode"
  copy_tree "$SHARED_AGENTS" "${HOME}/.config/opencode/agents"
  copy_file "$SHARED_PLUGIN" "${HOME}/.config/opencode/plugins/hooks.js"
  ensure_symlink "${HOME}/.config/opencode/AGENTS.md" "$SHARED_INSTRUCTIONS"
}

install_kilo() {
  log_info "installing for Kilo Code"

  ensure_dir "${HOME}/.config/kilo"
  copy_tree "$SHARED_AGENTS" "${HOME}/.config/kilo/agents"
  copy_file "$SHARED_PLUGIN" "${HOME}/.config/kilo/plugin/hooks.js"
  install_config "${HOME}/.config/kilo/kilo.jsonc" ".agents/skills" "$(kilo_config)"
}

install_copilot() {
  log_info "installing for GitHub Copilot"

  ensure_dir "${HOME}/.copilot"
  copy_tree "${CHECKOUT}/.github/agents" "${HOME}/.copilot/agents"
  install_config "${HOME}/.copilot/hooks/preflight.json" "$GATE_SCRIPT" "$(copilot_hooks)"
  ensure_symlink "${HOME}/.copilot/copilot-instructions.md" "$SHARED_INSTRUCTIONS"
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

# --- Reporting ---------------------------------------------------------------

announce_plan() {
  echo "==============================================================" >&2
  echo " agent-standards global install" >&2
  echo "==============================================================" >&2
  log_info "home directory: ${HOME}"
  log_info "shared checkout: ${CHECKOUT}"
  log_info "install source: ${REPO}"
  log_info "agents: $(join_spaces "${SELECTED[@]}")"
  echo "==============================================================" >&2
}

report_result() {
  echo "==============================================================" >&2

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

  ensure_checkout
  install_shared_tree

  local agent
  for agent in "${SELECTED[@]}"; do
    install_agent "$agent"
  done

  report_result
}

main "$@"
exit "$EXIT_CODE"
