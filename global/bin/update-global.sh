#!/bin/sh
# -----------------------------------------------------------------------------
# Script: update-global.sh
# Description: Updates the global agent-standards install in a home directory
#              from the committed state of the repository. The hook scripts, the
#              plugin and this updater are refreshed in full. Only the skills and
#              subagents already installed are refreshed, and none is ever added.
#              A file is removed only when the previously installed commit
#              shipped it and the new one no longer does.
# Usage: sh update-global.sh [--dry-run] [--source PATH|URL] [--home-dir DIR]
# Options:
#   --dry-run       List what would change and write nothing.
#   --source VALUE  A local clone, read at its HEAD commit, or a URL to clone.
#                   Default: https://github.com/Lukk17/agent-standards.git
#   --home-dir DIR  The home directory that holds the install. Default: $HOME.
#   -h, --help      Print this help and exit.
# Exit codes:
#   0  Updated, or the dry run listed what it would do.
#   1  No install was found, or a git step failed.
#   2  Bad arguments, or a required command is missing.
# Requires: a POSIX sh, git, tar, find, cmp, sort, awk, mktemp.
# -----------------------------------------------------------------------------
set -eu

LC_ALL=C
export LC_ALL

readonly UPSTREAM_URL='https://github.com/Lukk17/agent-standards.git'
readonly UPSTREAM_PATHS='.agents/hooks .agents/plugin global/bin .agents/skills .agents/agents .claude/agents .codex/agents .github/agents'
readonly WIRING_FILES='.claude/settings.json .codex/config.toml .github/hooks/preflight.json docs/GLOBAL_SETUP.md'
readonly SUBAGENT_TREES='.agents/agents:.agents/agents .claude/agents:.claude/agents .codex/agents:.codex/agents .copilot/agents:.github/agents'

dry_run=0
source_ref=$UPSTREAM_URL
home_dir=${HOME:-}
workspace=''
repo=''
tree=''
commit=''
old_commit=''
old_known=0
old_list=''

count_update=0
count_add=0
count_remove=0
count_unchanged=0
count_keep=0
count_skip=0

usage() {
  sed -n '/^# Script:/,/^# Requires:/s/^# \{0,1\}//p' "$0"
}

die() {
  printf 'update-global: %s\n' "$1" >&2
  exit "${2:-1}"
}

cleanup() {
  if [ -n "$workspace" ] && [ -d "$workspace" ]; then
    rm -rf -- "$workspace"
  fi
}

parse_args() {
  while [ $# -gt 0 ]; do
    case $1 in
      --dry-run) dry_run=1 ;;
      --source)
        [ $# -ge 2 ] || die '--source needs a value' 2
        source_ref=$2
        shift
        ;;
      --source=*) source_ref=${1#*=} ;;
      --home-dir)
        [ $# -ge 2 ] || die '--home-dir needs a value' 2
        home_dir=$2
        shift
        ;;
      --home-dir=*) home_dir=${1#*=} ;;
      -h|--help)
        usage
        exit 0
        ;;
      *) die "unknown argument: $1" 2 ;;
    esac
    shift
  done

  [ -n "$source_ref" ] || die '--source must not be empty' 2
  [ -n "$home_dir" ] || die 'no home directory: set HOME or pass --home-dir' 2
}

require_commands() {
  for required in git tar find cmp sort awk mktemp; do
    command -v "$required" >/dev/null 2>&1 || die "required command not found: $required" 2
  done
}

report() {
  printf '%-7s ~/%s%s\n' "$1" "$2" "${3:-}"
}

open_source() {
  if [ -d "$source_ref" ]; then
    repo=$source_ref
  else
    repo=$workspace/clone
    git clone --quiet --filter=blob:none "$source_ref" "$repo" || die "could not clone $source_ref"
  fi

  commit=$(git -C "$repo" rev-parse --verify --quiet 'HEAD^{commit}') || die "no committed HEAD in $source_ref"
}

extract_commit() {
  present=''
  for upstream_path in $UPSTREAM_PATHS; do
    if git -C "$repo" cat-file -e "$commit:$upstream_path" 2>/dev/null; then
      present="$present $upstream_path"
    fi
  done

  case $present in
    *' .agents/hooks'*) ;;
    *) die "$source_ref holds no .agents/hooks at $commit, so it is not an agent-standards repository" ;;
  esac

  tree=$workspace/tree
  mkdir "$tree"
  # shellcheck disable=SC2086  # $present is a space-separated list of plain repository paths
  git -C "$repo" archive --format=tar -o "$workspace/upstream.tar" "$commit" -- $present || die "git archive failed at $commit"
  tar -xf - -C "$tree" <"$workspace/upstream.tar" || die 'could not unpack the archive'
}

load_previous_commit() {
  old_list=$workspace/previous.list
  : >"$old_list"

  if [ -f "$home_dir/.agents/.upstream-commit" ]; then
    old_commit=$(tr -d ' \r\n' <"$home_dir/.agents/.upstream-commit")
  fi

  if [ -n "$old_commit" ] && git -C "$repo" cat-file -e "$old_commit^{commit}" 2>/dev/null; then
    # shellcheck disable=SC2086  # $UPSTREAM_PATHS is a space-separated list of plain repository paths
    git -C "$repo" -c core.quotePath=false ls-tree -r --name-only "$old_commit" -- $UPSTREAM_PATHS >"$old_list" ||
      die "git ls-tree failed at $old_commit"
    old_known=1
  fi
}

shipped_before() {
  [ "$old_known" -eq 1 ] && grep -qxF -- "$1" "$old_list"
}

shipped_before_under() {
  [ "$old_known" -eq 1 ] || return 1

  while IFS= read -r shipped_path; do
    case $shipped_path in
      "$1/"*) return 0 ;;
    esac
  done <"$old_list"

  return 1
}

put_file() {
  put_target=$home_dir/$2

  if [ -f "$put_target" ]; then
    if cmp -s "$1" "$put_target"; then
      count_unchanged=$((count_unchanged + 1))
      return 0
    fi
    report update "$2"
    count_update=$((count_update + 1))
  elif [ -e "$put_target" ]; then
    report skip "$2" ' (not a regular file, left alone)'
    count_skip=$((count_skip + 1))
    return 0
  else
    report add "$2"
    count_add=$((count_add + 1))
  fi

  if [ "$dry_run" -eq 0 ]; then
    mkdir -p "$(dirname "$put_target")"
    cp "$1" "$put_target"
  fi
}

remove_empty_parents() {
  empty_dir=$(dirname "$1")
  while [ "$empty_dir" != "$2" ] && rmdir "$empty_dir" 2>/dev/null; do
    empty_dir=$(dirname "$empty_dir")
  done
}

prune() {
  [ "$old_known" -eq 1 ] || return 0

  awk -v prefix="$1/" 'index($0, prefix) == 1 { print substr($0, length(prefix) + 1) }' "$old_list" >"$workspace/prune.list"

  while IFS= read -r prune_rel; do
    [ -e "$tree/$1/$prune_rel" ] && continue
    [ -f "$home_dir/$2/$prune_rel" ] || continue

    report remove "$2/$prune_rel"
    count_remove=$((count_remove + 1))

    if [ "$dry_run" -eq 0 ]; then
      rm -f -- "$home_dir/$2/$prune_rel"
      remove_empty_parents "$home_dir/$2/$prune_rel" "$home_dir/$2"
    fi
  done <"$workspace/prune.list"
}

mirror() {
  if [ -d "$tree/$1" ]; then
    (cd "$tree/$1" && find . -type f) | sed 's|^\./||' | sort >"$workspace/mirror.list"

    while IFS= read -r mirror_rel; do
      put_file "$tree/$1/$mirror_rel" "$2/$mirror_rel"
    done <"$workspace/mirror.list"
  fi

  prune "$1" "$2"
}

update_tooling() {
  mirror .agents/hooks .agents/hooks
  mirror .agents/plugin .agents/plugin
  mirror global/bin .agents/bin
}

update_skills() {
  for skill_dir in "$home_dir/.agents/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")

    if [ -d "$tree/.agents/skills/$skill_name" ]; then
      mirror ".agents/skills/$skill_name" ".agents/skills/$skill_name"
    elif shipped_before_under ".agents/skills/$skill_name"; then
      report keep ".agents/skills/$skill_name" ' (removed upstream, left in place)'
      count_keep=$((count_keep + 1))
    else
      report skip ".agents/skills/$skill_name" ' (not an upstream skill)'
      count_skip=$((count_skip + 1))
    fi
  done
}

update_subagents() {
  for subagent_pair in $SUBAGENT_TREES; do
    subagent_home=${subagent_pair%%:*}
    subagent_upstream=${subagent_pair#*:}
    [ -d "$home_dir/$subagent_home" ] || continue

    for subagent_file in "$home_dir/$subagent_home"/*; do
      [ -f "$subagent_file" ] || continue
      subagent_name=${subagent_file##*/}

      if [ -f "$tree/$subagent_upstream/$subagent_name" ]; then
        put_file "$tree/$subagent_upstream/$subagent_name" "$subagent_home/$subagent_name"
      elif shipped_before "$subagent_upstream/$subagent_name"; then
        report keep "$subagent_home/$subagent_name" ' (removed upstream, left in place)'
        count_keep=$((count_keep + 1))
      else
        report skip "$subagent_home/$subagent_name" ' (not an upstream subagent)'
        count_skip=$((count_skip + 1))
      fi
    done
  done
}

report_wiring() {
  if [ "$old_known" -eq 0 ]; then
    printf 'Hook wiring: the previously installed commit is unknown here, so files removed upstream were not detected\n'
    printf 'and wiring changes could not be listed. Compare the per-agent blocks in docs/GLOBAL_SETUP.md by hand.\n'
    return 0
  fi

  # shellcheck disable=SC2086  # $WIRING_FILES is a space-separated list of plain repository paths
  wiring_changed=$(git -C "$repo" diff --name-only "$old_commit" "$commit" -- $WIRING_FILES) ||
    die "git diff failed between $old_commit and $commit"

  if [ -z "$wiring_changed" ]; then
    printf 'Hook wiring: unchanged upstream since %s.\n' "$old_commit"
    return 0
  fi

  printf 'Hook wiring changed upstream since %s. Merge it into your own files by hand, from docs/GLOBAL_SETUP.md:\n' "$old_commit"
  printf '%s\n' "$wiring_changed" | sed 's/^/  /'
  printf 'See the change with: git diff %s %s -- %s\n' "$old_commit" "$commit" "$WIRING_FILES"
}

record_commit() {
  if [ "$dry_run" -eq 1 ]; then
    printf 'Would record %s in ~/.agents/.upstream-commit.\n' "$commit"
    return 0
  fi

  printf '%s\n' "$commit" >"$home_dir/.agents/.upstream-commit"
  printf 'Recorded %s in ~/.agents/.upstream-commit.\n' "$commit"
}

report_totals() {
  if [ "$dry_run" -eq 1 ]; then
    printf 'Dry run, nothing was written. Would update %d, add %d, remove %d. Unchanged %d.' \
      "$count_update" "$count_add" "$count_remove" "$count_unchanged"
  else
    printf 'Updated %d, added %d, removed %d. Unchanged %d.' \
      "$count_update" "$count_add" "$count_remove" "$count_unchanged"
  fi
  printf ' Left alone: %d removed upstream, %d not from upstream.\n' "$count_keep" "$count_skip"
}

main() {
  parse_args "$@"
  require_commands

  [ -d "$home_dir/.agents" ] || die "no global install at $home_dir/.agents; install it first, see docs/GLOBAL_SETUP.md"

  workspace=$(mktemp -d)
  trap cleanup EXIT
  trap 'exit 130' INT TERM

  open_source
  extract_commit
  load_previous_commit

  if [ "$dry_run" -eq 1 ]; then
    printf 'agent-standards global update, dry run\n'
  else
    printf 'agent-standards global update\n'
  fi
  printf 'Source: %s at %s\n' "$source_ref" "$commit"
  printf 'Home:   %s\n' "$home_dir"

  update_tooling
  update_skills
  update_subagents
  report_wiring
  record_commit
  report_totals
}

main "$@"
