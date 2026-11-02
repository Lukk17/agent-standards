#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: cleanup-leftovers.sh
# Description: Finds leftovers that nothing on the machine uses any more and, with --clean, removes each group only after you answer y.
# Usage: cleanup-leftovers.sh [--clean]
# Requires: Bash 4.4 or newer, GNU coreutils, find, grep, gzip, od
# Options:
#   (no option)   Scan only. Print one line per group with what was found and its size. Remove nothing.
#   --clean       Show each group that has something, ask "Remove? [y/N]" and remove it only on y.
#   -h, --help    Print this help and exit.
# Groups:
#   a) pacman cache: files of packages no longer installed, and old versions beyond the last 2
#   b) orphan packages from pacman -Qtdq, without kernels, microcode, firmware, drivers, boot and init packages
#   c) AUR build folders in ~/.cache/paru/clone whose package is no longer installed
#   d) Docker: dangling images no container uses, and the build cache
#   e) Flatpak runtimes no app needs
#   f) JetBrains folders of IDE versions that are no longer installed
#   g) Trash
#   h) thumbnails whose original file no longer exists
# Run it as your own user. Steps that need root call sudo after your y, so you see the password prompt.
# A group whose tool is missing is skipped with one line saying so.
# Exit codes:
#   0  success
#   1  general error
#   2  misuse (bad argument, HOME not usable)
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'
shopt -s nullglob

readonly CACHE_HOME="${XDG_CACHE_HOME:-${HOME:-}/.cache}"
readonly DATA_HOME="${XDG_DATA_HOME:-${HOME:-}/.local/share}"
readonly CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME:-}/.config}"
readonly PARU_CLONE_DIR="$CACHE_HOME/paru/clone"
readonly TRASH_DIR="$DATA_HOME/Trash"
readonly THUMBNAIL_DIR="$CACHE_HOME/thumbnails"
readonly JETBRAINS_ROOTS=("$CACHE_HOME/JetBrains" "$DATA_HOME/JetBrains" "$CONFIG_HOME/JetBrains")
readonly JETBRAINS_TOOLBOX_SETTINGS="$DATA_HOME/JetBrains/Toolbox/.settings.json"
readonly JETBRAINS_VERSION_FOLDER='^[A-Za-z][A-Za-z-]*[0-9]{4}\.[0-9]+$'
readonly GZIP_HEADER='\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
readonly THUMBNAIL_LIST_LIMIT=20

clean=0

usage() {
  sed -n '3,/^# --*$/{/^# --*$/d;s/^# //;p;}' "$0"
  exit "${1:-0}"
}

say() { printf '%s\n' "$*"; }

has() { command -v "$1" >/dev/null 2>&1; }

confirm() {
  local answer=""
  printf 'Remove? [y/N] '
  IFS= read -r answer || printf '\n'
  [[ $answer == [yY] ]]
}

run_as_root() {
  local IFS=' '
  if ! has sudo; then
    say "sudo is not installed, run this as root yourself: $*"
    return 1
  fi
  sudo "$@"
}

size_of() {
  if (( $# == 0 )); then
    printf '0'
    return 0
  fi
  { printf '%s\0' "$@" | du -sch --files0-from=- 2>/dev/null || true; } | tail -n 1 | cut -f 1
}

is_under() {
  local parent_real target_parent_real home_real
  parent_real="$(realpath -e -- "$1" 2>/dev/null)" || return 1
  target_parent_real="$(realpath -e -- "$(dirname -- "$2")" 2>/dev/null)" || return 1
  home_real="$(realpath -e -- "$HOME" 2>/dev/null)" || return 1
  [[ $parent_real != / && $parent_real != "$home_real" ]] || return 1
  [[ "$target_parent_real/" == "$parent_real"/* ]]
}

remove_dir_under() {
  local parent=$1 target=$2
  [[ -n $target && -d $target && ! -L $target ]] || return 1
  is_under "$parent" "$target" || return 1
  rm -rf -- "$target"
}

remove_file_under() {
  local parent=$1 target=$2
  [[ -n $target && -f $target && ! -L $target ]] || return 1
  is_under "$parent" "$target" || return 1
  rm -f -- "$target"
}

paccache_summary() {
  local output line
  output="$(LC_ALL=C paccache --nocolor -d "$@" 2>/dev/null || true)"
  line="$(grep 'finished dry run' <<<"$output" | tail -n 1 || true)"
  if [[ -z $line ]]; then
    printf 'nothing'
    return 0
  fi
  sed -n 's/.*finished dry run: \([0-9]*\) candidates (disk space saved: \(.*\))/\1 files, \2/p' <<<"$line"
}

clean_paccache() {
  local dry_flags=$1 remove_flags=$2 label=$3 summary
  summary="$(paccache_summary "$dry_flags")"
  if [[ $summary == nothing ]]; then
    say "a) $label: nothing to remove"
    return 0
  fi
  say "a) $label: $summary"
  LC_ALL=C paccache --nocolor -dv "$dry_flags" 2>/dev/null | grep -v '^==>' || true
  if ! confirm; then
    say "a) kept $label"
    return 0
  fi
  if run_as_root paccache "$remove_flags"; then
    say "a) removed $label"
  else
    say "a) paccache failed, $label kept"
  fi
}

section_pacman_cache() {
  if ! has paccache; then
    say "a) pacman cache: skipped, paccache is not installed (it comes with pacman-contrib)"
    return 0
  fi
  say "a) pacman cache: packages no longer installed: $(paccache_summary -uk0). Old versions beyond the last 2: $(paccache_summary -k2)."
  (( clean )) || return 0
  clean_paccache -uk0 -ruk0 "package files of packages no longer installed"
  clean_paccache -k2 -rk2 "old package versions beyond the last 2"
}

is_protected_package() {
  case "$1" in
    linux* | *-ucode | nvidia* | mkinitcpio* | limine* | plymouth* | systemd* | snap*) return 0 ;;
    *) return 1 ;;
  esac
}

package_sizes() {
  LC_ALL=C pacman -Qi "$@" 2>/dev/null | awk '
    $1 == "Name" { name = $3 }
    $1 == "Installed" && $2 == "Size" { printf "%s\t%s %s\n", name, $4, $5 }
  ' || true
}

total_of_sizes() {
  awk -F '\t' '
    BEGIN { unit["B"] = 1; unit["KiB"] = 1024; unit["MiB"] = 1048576; unit["GiB"] = 1073741824; unit["TiB"] = 1099511627776 }
    { split($2, part, " "); total += part[1] * unit[part[2]] }
    END { printf "%.1f MiB", total / 1048576 }
  '
}

section_orphans() {
  if ! has pacman; then
    say "b) orphan packages: skipped, pacman is not installed"
    return 0
  fi
  local orphans=() offered=() kept=() name sizes
  mapfile -t orphans < <(pacman -Qtdq 2>/dev/null || true)
  for name in "${orphans[@]}"; do
    [[ -n $name ]] || continue
    if is_protected_package "$name"; then
      kept+=("$name")
    else
      offered+=("$name")
    fi
  done
  local kept_text="none"
  (( ${#kept[@]} == 0 )) || kept_text="$(IFS=' '; printf '%s' "${kept[*]}")"
  if (( ${#offered[@]} == 0 )); then
    say "b) orphan packages: none to remove. Kept as protected: $kept_text"
    return 0
  fi
  sizes="$(package_sizes "${offered[@]}")"
  say "b) orphan packages: ${#offered[@]} to remove ($(total_of_sizes <<<"$sizes")). Kept as protected: $kept_text"
  (( clean )) || return 0
  printf '%s\n' "$sizes" | sed 's/^/  /'
  if ! confirm; then
    say "b) kept the orphan packages"
    return 0
  fi
  if run_as_root pacman -Rns "${offered[@]}"; then
    say "b) removed ${#offered[@]} orphan packages"
  else
    say "b) pacman did not remove the orphan packages"
  fi
}

srcinfo_names() {
  sed -n 's/^\(pkgbase\|pkgname\) = //p' -- "$1" 2>/dev/null || true
}

section_aur_builds() {
  if ! has paru; then
    say "c) AUR build folders: skipped, paru is not installed"
    return 0
  fi
  if [[ ! -d $PARU_CLONE_DIR ]]; then
    say "c) AUR build folders: none, $PARU_CLONE_DIR does not exist"
    return 0
  fi
  if pgrep -x makepkg >/dev/null 2>&1 || pgrep -x paru >/dev/null 2>&1; then
    say "c) AUR build folders: skipped, a makepkg or paru process is running"
    return 0
  fi
  local -A installed=()
  local name dir in_use candidate stale=() unknown=0
  while IFS= read -r name; do
    if [[ -n $name ]]; then
      installed["$name"]=1
    fi
  done < <(pacman -Qq 2>/dev/null || true)
  for dir in "$PARU_CLONE_DIR"/*/; do
    dir="${dir%/}"
    if [[ -L $dir || ! -f $dir/.SRCINFO ]]; then
      unknown=$(( unknown + 1 ))
      continue
    fi
    in_use=0
    while IFS= read -r candidate; do
      if [[ -n $candidate && -n ${installed[$candidate]:-} ]]; then
        in_use=1
      fi
    done < <(printf '%s\n' "${dir##*/}"; srcinfo_names "$dir/.SRCINFO")
    (( in_use )) || stale+=("$dir")
  done
  say "c) AUR build folders of packages no longer installed: ${#stale[@]} ($(size_of "${stale[@]}")). Kept because they have no .SRCINFO: $unknown"
  (( clean )) || return 0
  (( ${#stale[@]} > 0 )) || return 0
  for dir in "${stale[@]}"; do
    say "  $dir $(size_of "$dir")"
  done
  if ! confirm; then
    say "c) kept the AUR build folders"
    return 0
  fi
  for dir in "${stale[@]}"; do
    if remove_dir_under "$PARU_CLONE_DIR" "$dir"; then
      say "c) removed $dir"
    else
      say "c) could not remove $dir, kept"
    fi
  done
}

docker_df_field() {
  docker system df --format '{{.Type}}'$'\t''{{.TotalCount}}'$'\t''{{.Size}}'$'\t''{{.Reclaimable}}' 2>/dev/null \
    | awk -F '\t' -v type="$1" -v field="$2" '$1 == type { print $field }' || true
}

docker_storage_note() {
  local driver_status root_dir
  driver_status="$(docker info --format '{{json .DriverStatus}}' 2>/dev/null || true)"
  root_dir="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
  if [[ $driver_status == *io.containerd.snapshotter* ]]; then
    say "d) note: Docker uses the containerd image store, so images live in /var/lib/containerd. Measure it with: sudo du -xsh /var/lib/containerd"
  else
    say "d) note: images live in ${root_dir:-/var/lib/docker}, and in /var/lib/containerd when Docker uses the containerd image store"
  fi
}

section_docker() {
  if ! has docker; then
    say "d) Docker: skipped, docker is not installed"
    return 0
  fi
  if ! docker info >/dev/null 2>&1; then
    say "d) Docker: skipped, the Docker daemon is not reachable"
    return 0
  fi
  local line id size index offered=() offered_sizes=() in_use_count=0 cache_count cache_size
  while IFS=$'\t' read -r id size; do
    [[ -n $id ]] || continue
    if [[ -n "$(docker ps -a -q --filter "ancestor=$id" 2>/dev/null || true)" ]]; then
      in_use_count=$(( in_use_count + 1 ))
    else
      offered+=("$id")
      offered_sizes+=("$size")
    fi
  done < <(docker image ls --filter dangling=true --format '{{.ID}}'$'\t''{{.Size}}' 2>/dev/null || true)
  cache_count="$(docker_df_field 'Build Cache' 2)"
  cache_size="$(docker_df_field 'Build Cache' 3)"
  line="d) Docker: dangling images no container uses: ${#offered[@]} ($(IFS=' '; printf '%s' "${offered_sizes[*]:-0B}"))."
  line+=" Dangling images kept because a container uses them: $in_use_count. Build cache: ${cache_size:-0B}."
  line+=" All images $(docker_df_field Images 3), reclaimable $(docker_df_field Images 4). Stopped containers, named images and volumes always stay."
  say "$line"
  docker_storage_note
  (( clean )) || return 0
  if (( ${#offered[@]} > 0 )); then
    for index in "${!offered[@]}"; do
      say "  ${offered[index]} ${offered_sizes[index]}"
    done
    if confirm; then
      if docker image prune; then
        say "d) ran docker image prune for the dangling images"
      else
        say "d) docker image prune failed"
      fi
    else
      say "d) kept the dangling images"
    fi
  fi
  if [[ ${cache_count:-0} =~ ^[0-9]+$ ]] && (( cache_count > 0 )); then
    say "  build cache ${cache_size}"
    if confirm; then
      if docker builder prune; then
        say "d) ran docker builder prune for the build cache"
      else
        say "d) docker builder prune failed"
      fi
    else
      say "d) kept the build cache"
    fi
  fi
}

section_flatpak() {
  if ! has flatpak; then
    say "e) Flatpak: skipped, flatpak is not installed"
    return 0
  fi
  local runtimes
  runtimes="$(flatpak list --runtime --columns=application 2>/dev/null | grep -c . || true)"
  say "e) Flatpak: ${runtimes:-0} runtimes installed. flatpak itself finds the ones no app needs and shows them with sizes in --clean mode."
  (( clean )) || return 0
  say "e) running flatpak uninstall --unused, it lists what it would remove and asks itself"
  if flatpak uninstall --unused; then
    say "e) flatpak uninstall --unused finished"
  else
    say "e) flatpak uninstall --unused failed or was cancelled"
  fi
}

toolbox_install_location() {
  [[ -f $JETBRAINS_TOOLBOX_SETTINGS ]] || return 0
  local location
  location="$(sed -n 's/.*"install_location"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' -- "$JETBRAINS_TOOLBOX_SETTINGS" | head -n 1 || true)"
  [[ -n $location ]] || return 0
  if [[ $location == \~/* ]]; then
    location="$HOME/${location:2}"
  fi
  printf '%s\n' "$location"
}

installed_jetbrains_versions() {
  local root depth info
  {
    toolbox_install_location
    printf '%s\n' "$DATA_HOME/JetBrains/Toolbox/apps" /opt /usr/share /usr/lib /snap
  } | while IFS= read -r root; do
    [[ -n $root && -d $root ]] || continue
    depth=3
    if [[ $root == "$HOME"/* ]]; then
      depth=4
    fi
    while IFS= read -r -d '' info; do
      sed -n 's/.*"dataDirectoryName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' -- "$info" 2>/dev/null || true
    done < <(find "$root" -maxdepth "$depth" -type f -name product-info.json -print0 2>/dev/null || true)
  done | sort -u
}

section_jetbrains() {
  local -A installed=()
  local version root dir name stale=() installed_list=()
  while IFS= read -r version; do
    [[ -n $version ]] || continue
    installed["$version"]=1
    installed_list+=("$version")
  done < <(installed_jetbrains_versions)
  if (( ${#installed_list[@]} == 0 )); then
    say "f) JetBrains: skipped, no installed IDE was found (no product-info.json), so no folder is offered"
    return 0
  fi
  for root in "${JETBRAINS_ROOTS[@]}"; do
    [[ -d $root && ! -L $root ]] || continue
    for dir in "$root"/*/; do
      dir="${dir%/}"
      name="${dir##*/}"
      [[ ! -L $dir && $name =~ $JETBRAINS_VERSION_FOLDER ]] || continue
      [[ -n ${installed[$name]:-} ]] || stale+=("$dir")
    done
  done
  say "f) JetBrains folders of IDE versions no longer installed: ${#stale[@]} ($(size_of "${stale[@]}")). Installed versions: $(IFS=' '; printf '%s' "${installed_list[*]}")"
  (( clean )) || return 0
  for dir in "${stale[@]}"; do
    say "  $dir $(size_of "$dir")"
    if ! confirm; then
      say "f) kept $dir"
      continue
    fi
    root="$(dirname -- "$dir")"
    if remove_dir_under "$root" "$dir"; then
      say "f) removed $dir"
    else
      say "f) could not remove $dir, kept"
    fi
  done
}

empty_trash_directly() {
  local sub entry
  for sub in files info expunged; do
    [[ -d $TRASH_DIR/$sub && ! -L $TRASH_DIR/$sub ]] || continue
    while IFS= read -r -d '' entry; do
      if ! is_under "$TRASH_DIR/$sub" "$entry" || ! rm -rf -- "$entry"; then
        say "g) could not remove $entry"
      fi
    done < <(find "$TRASH_DIR/$sub" -mindepth 1 -maxdepth 1 -print0 2>/dev/null || true)
  done
}

trash_count() {
  find "$TRASH_DIR/files" -mindepth 1 -maxdepth 1 2>/dev/null | grep -c . || true
}

section_trash() {
  local count
  if [[ ! -d $TRASH_DIR/files || -L $TRASH_DIR ]]; then
    say "g) Trash: empty"
    return 0
  fi
  count="$(trash_count)"
  if (( count == 0 )); then
    say "g) Trash: empty"
    return 0
  fi
  say "g) Trash: $count items ($(size_of "$TRASH_DIR/files"))"
  (( clean )) || return 0
  if ! confirm; then
    say "g) kept the Trash"
    return 0
  fi
  empty_trash_directly
  say "g) emptied $TRASH_DIR"
  say "g) Trash now holds $(trash_count) items"
}

thumbnail_uri() {
  local file=$1 match offset kind header length text_length key_end
  match="$(LC_ALL=C grep -abo -m 1 -E '(tEXt|zTXt)Thumb::URI' -- "$file" 2>/dev/null | head -n 1 || true)"
  offset="${match%%:*}"
  kind="${match#*:}"
  kind="${kind:0:4}"
  [[ $offset =~ ^[0-9]+$ ]] && (( offset >= 4 )) || return 0
  IFS=' ' read -r -a header < <(od -An -v -w19 -tu1 -j "$(( offset - 4 ))" -N 19 -- "$file" 2>/dev/null || true) || true
  (( ${#header[@]} == 19 && header[18] == 0 )) || return 0
  length=$(( (header[0] << 24) | (header[1] << 16) | (header[2] << 8) | header[3] ))
  text_length=$(( length - 11 ))
  key_end=$(( offset + 4 + 11 ))
  (( text_length > 0 && text_length < 65536 )) || return 0
  if [[ $kind == tEXt ]]; then
    tail -c "+$(( key_end + 1 ))" -- "$file" 2>/dev/null | head -c "$text_length" || true
  elif (( text_length > 3 )); then
    { printf '%b' "$GZIP_HEADER"; tail -c "+$(( key_end + 4 ))" -- "$file" 2>/dev/null | head -c "$(( text_length - 3 ))" || true; } | gzip -dc 2>/dev/null || true
  fi
}

uri_to_path() {
  local path="${1#file://}"
  [[ $1 == file:///* && $path != *\\* ]] || return 1
  printf '%b' "${path//%/\\x}"
}

stale_thumbnails() {
  local png uri original
  while IFS= read -r -d '' png; do
    uri="$(thumbnail_uri "$png")"
    original="$(uri_to_path "$uri")" || continue
    [[ -n $original && ! -e $original ]] || continue
    printf '%s\0%s\0' "$png" "$original"
  done < <(find "$THUMBNAIL_DIR" -type f -name '*.png' -print0 2>/dev/null || true)
}

section_thumbnails() {
  if [[ ! -d $THUMBNAIL_DIR || -L $THUMBNAIL_DIR ]]; then
    say "h) thumbnails: none, $THUMBNAIL_DIR does not exist"
    return 0
  fi
  local pairs=() thumbnails=() originals=() index removed=0 total
  mapfile -d '' pairs < <(stale_thumbnails)
  for (( index = 0; index + 1 < ${#pairs[@]}; index += 2 )); do
    thumbnails+=("${pairs[index]}")
    originals+=("${pairs[index + 1]}")
  done
  total="$(find "$THUMBNAIL_DIR" -type f -name '*.png' 2>/dev/null | grep -c . || true)"
  say "h) thumbnails whose original file no longer exists: ${#thumbnails[@]} of $total ($(size_of "${thumbnails[@]}"))"
  (( clean )) || return 0
  (( ${#thumbnails[@]} > 0 )) || return 0
  for (( index = 0; index < ${#originals[@]} && index < THUMBNAIL_LIST_LIMIT; index++ )); do
    say "  ${originals[index]}"
  done
  (( ${#originals[@]} <= THUMBNAIL_LIST_LIMIT )) || say "  and $(( ${#originals[@]} - THUMBNAIL_LIST_LIMIT )) more"
  if ! confirm; then
    say "h) kept the thumbnails"
    return 0
  fi
  for index in "${!thumbnails[@]}"; do
    if remove_file_under "$THUMBNAIL_DIR" "${thumbnails[index]}"; then
      removed=$(( removed + 1 ))
    fi
  done
  say "h) removed $removed thumbnails"
}

main() {
  case "${1:-}" in
    "") ;;
    --clean) clean=1 ;;
    -h | --help) usage ;;
    *) usage 2 >&2 ;;
  esac
  (( $# <= 1 )) || usage 2 >&2
  if [[ -z ${HOME:-} || $HOME == / || ! -d $HOME ]]; then
    say "HOME is not set to a home folder, stopping" >&2
    return 2
  fi
  if (( clean )); then
    say "Clean mode: every group asks before it removes anything."
  else
    say "Scan only, nothing is removed. Run with --clean to remove after a y answer."
  fi
  section_pacman_cache
  section_orphans
  section_aur_builds
  section_docker
  section_flatpak
  section_jetbrains
  section_trash
  section_thumbnails
}

main "$@"
