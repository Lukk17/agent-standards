#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: test-cleanup-leftovers.sh
# Description: Tests cleanup-leftovers.sh with fake data and stubbed tools. Runs only inside the throwaway container that run-tests.sh creates.
# Usage: test-cleanup-leftovers.sh
# Requires: Bash 4.4 or newer, an archlinux image, the file /.dockerenv
# Exit codes:
#   0  every test passed
#   1  a test failed
#   2  not running inside a container
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TESTS_DIR
readonly SCRIPT="$TESTS_DIR/../cleanup-leftovers.sh"
readonly BASE_PATH="/usr/local/sbin:/usr/local/bin:/usr/bin"

passed=0
failed=0
failures=()

fail() {
  printf 'FAIL %s: %s\n' "$current_test" "$*" >&2
  exit 1
}

assert_contains() {
  [[ $1 == *"$2"* ]] || fail "output does not contain [$2]. Output was:"$'\n'"$1"
}

assert_not_contains() {
  [[ $1 != *"$2"* ]] || fail "output contains [$2]. Output was:"$'\n'"$1"
}

assert_exists() {
  [[ -e $1 ]] || fail "$1 is missing"
}

assert_missing() {
  [[ ! -e $1 ]] || fail "$1 still exists"
}

assert_equal() {
  [[ $1 == "$2" ]] || fail "expected [$2], got [$1]"
}

write_stub() {
  local name=$1
  cat >"$STUB_DIR/$name"
  chmod +x "$STUB_DIR/$name"
}

stub_pacman() {
  write_stub pacman <<'EOF'
#!/usr/bin/env bash
printf 'pacman %s\n' "$*" >>"$CALL_LOG"
case "$1" in
  -Qtdq)
    [[ -s $FAKE_DIR/orphans ]] || exit 1
    cat "$FAKE_DIR/orphans"
    ;;
  -Qq) cat "$FAKE_DIR/installed" 2>/dev/null || true ;;
  -Qi)
    shift
    for name in "$@"; do
      printf 'Name            : %s\nVersion         : 1.0-1\nInstalled Size  : 2.00 MiB\n\n' "$name"
    done
    ;;
esac
exit 0
EOF
}

stub_sudo() {
  write_stub sudo <<'EOF'
#!/usr/bin/env bash
printf 'sudo %s\n' "$*" >>"$CALL_LOG"
"$@"
EOF
}

stub_paccache() {
  write_stub paccache <<'EOF'
#!/usr/bin/env bash
printf 'paccache %s\n' "$*" >>"$CALL_LOG"
case "$*" in
  *-d*-uk0*) printf '==> Candidate packages:\nold-tool (x86_64):\n  old-tool-1.0-1-x86_64.pkg.tar.zst\n==> finished dry run: 2 candidates (disk space saved: 10.00 MiB)\n' ;;
  *-d*-k2*) printf '==> no candidate packages found for pruning\n' ;;
esac
EOF
}

stub_paru() {
  write_stub paru <<'EOF'
#!/usr/bin/env bash
printf 'paru %s\n' "$*" >>"$CALL_LOG"
EOF
}

stub_pgrep() {
  write_stub pgrep <<'EOF'
#!/usr/bin/env bash
printf 'pgrep %s\n' "$*" >>"$CALL_LOG"
[[ -n ${FAKE_RUNNING:-} && " $* " == *" $FAKE_RUNNING "* ]] && { echo 4242; exit 0; }
exit 1
EOF
}

stub_docker() {
  write_stub docker <<'EOF'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >>"$CALL_LOG"
case "$*" in
  "info --format {{json .DriverStatus}}") echo '[["driver-type","io.containerd.snapshotter.v1"]]' ;;
  "info --format {{.DockerRootDir}}") echo /var/lib/docker ;;
  info) echo 'Server: fake' ;;
  "image ls --filter dangling=true"*) printf 'sha256aaa\t10MB\nsha256bbb\t5MB\n' ;;
  "ps -a -q --filter ancestor=sha256bbb") echo c0ffee ;;
  "ps -a -q --filter ancestor="*) ;;
  "system df --format"*) printf 'Images\t5\t2GB\t1GB (50%%)\nContainers\t3\t1MB\t0B (0%%)\nLocal Volumes\t2\t1GB\t0B (0%%)\nBuild Cache\t4\t300MB\t300MB\n' ;;
esac
exit 0
EOF
}

stub_flatpak() {
  write_stub flatpak <<'EOF'
#!/usr/bin/env bash
printf 'flatpak %s\n' "$*" >>"$CALL_LOG"
case "$*" in
  "list --runtime --columns=application") printf 'org.freedesktop.Platform\norg.kde.Platform\norg.gnome.Platform\n' ;;
esac
exit 0
EOF
}

stub_gio() {
  local status=$1
  write_stub gio <<EOF
#!/usr/bin/env bash
printf 'gio %s\n' "\$*" >>"\$CALL_LOG"
exit $status
EOF
}

text_hex() {
  printf '%s' "$1" | od -An -v -tx1 | tr -d ' \n'
}

hex_bytes() {
  local index escaped=""
  for (( index = 0; index < ${#1}; index += 2 )); do
    escaped+="\\x${1:index:2}"
  done
  printf '%b' "$escaped"
}

adler32_hex() {
  local a=1 b=0 byte
  for byte in $(printf '%s' "$1" | od -An -v -tu1 | tr -s ' ' '\n'); do
    [[ -n $byte ]] || continue
    a=$(( (a + byte) % 65521 ))
    b=$(( (b + a) % 65521 ))
  done
  printf '%08x' $(( (b << 16) | a ))
}

zlib_hex() {
  local deflate
  deflate="$(printf '%s' "$1" | gzip -n -c | od -An -v -tx1 | tr -d ' \n')"
  deflate="${deflate:20}"
  deflate="${deflate:0:${#deflate}-16}"
  printf '789c%s%s' "$deflate" "$(adler32_hex "$1")"
}

png_chunk_hex() {
  local type_hex data_hex=$2
  type_hex="$(text_hex "$1")"
  printf '%08x%s%s00000000' "$(( ${#data_hex} / 2 ))" "$type_hex" "$data_hex"
}

make_png() {
  local file=$1 kind=$2 uri=${3:-} body
  body="89504e470d0a1a0a"
  body+="$(png_chunk_hex IHDR 0000000100000001080600000000)"
  body+="$(png_chunk_hex tEXt "$(text_hex 'Thumb::MTime')00$(text_hex 1700000000)")"
  case "$kind" in
    tEXt) body+="$(png_chunk_hex tEXt "$(text_hex 'Thumb::URI')00$(text_hex "$uri")")" ;;
    zTXt) body+="$(png_chunk_hex zTXt "$(text_hex 'Thumb::URI')0000$(zlib_hex "$uri")")" ;;
  esac
  body+="$(png_chunk_hex IDAT 789c636000000000010001)"
  body+="$(png_chunk_hex IEND '')"
  mkdir -p "$(dirname "$file")"
  hex_bytes "$body" >"$file"
}

tree_state() {
  find "$HOME" -printf '%y %s %p\n' | sort
}

run_script() {
  local status=0
  OUTPUT="$(PATH="$STUB_DIR:$BASE_PATH" "$SCRIPT" "$@" 2>&1)" || status=$?
  STATUS=$status
}

setup() {
  WORK_DIR="$(mktemp -d)"
  export HOME="$WORK_DIR/home"
  export FAKE_DIR="$WORK_DIR/fake"
  export CALL_LOG="$WORK_DIR/calls.log"
  STUB_DIR="$WORK_DIR/stubs"
  mkdir -p "$HOME" "$FAKE_DIR" "$STUB_DIR"
  : >"$CALL_LOG"
  : >"$FAKE_DIR/installed"
  unset XDG_CACHE_HOME XDG_DATA_HOME XDG_CONFIG_HOME FAKE_RUNNING
  stub_pacman
  stub_sudo
  stub_pgrep
  stub_gio 1
}

calls() {
  cat "$CALL_LOG"
}

fill_every_group() {
  stub_paccache
  stub_paru
  stub_docker
  stub_flatpak
  printf 'python-build\nlinux-lts\n' >"$FAKE_DIR/orphans"
  mkdir -p "$HOME/.cache/paru/clone/gone"
  printf 'pkgbase = gone\n\tpkgver = 1\npkgname = gone\n' >"$HOME/.cache/paru/clone/gone/.SRCINFO"
  mkdir -p "$HOME/.local/share/JetBrains/Toolbox/apps/idea" "$HOME/.cache/JetBrains/IntelliJIdea2025.1"
  printf '{\n  "dataDirectoryName": "IntelliJIdea2026.2"\n}\n' >"$HOME/.local/share/JetBrains/Toolbox/apps/idea/product-info.json"
  mkdir -p "$HOME/.local/share/Trash/files/old-folder" "$HOME/.local/share/Trash/info"
  printf 'x' >"$HOME/.local/share/Trash/files/old-file.txt"
  make_png "$HOME/.cache/thumbnails/normal/a.png" tEXt "file:///nowhere/gone.jpg"
}

test_help_prints_usage_and_exits_0() {
  run_script --help
  assert_equal "$STATUS" 0
  assert_contains "$OUTPUT" "Usage: cleanup-leftovers.sh [--clean]"
  assert_contains "$OUTPUT" "h) thumbnails whose original file no longer exists"
}

test_unknown_argument_exits_2() {
  run_script --bogus
  assert_equal "$STATUS" 2
  assert_contains "$OUTPUT" "Usage:"
}

test_two_arguments_exit_2() {
  run_script --clean --clean
  assert_equal "$STATUS" 2
}

test_home_set_to_root_exits_2() {
  local status=0
  OUTPUT="$(HOME=/ PATH="$STUB_DIR:$BASE_PATH" "$SCRIPT" 2>&1)" || status=$?
  assert_equal "$status" 2
  assert_contains "$OUTPUT" "HOME is not set to a home folder"
}

test_missing_tools_are_skipped() {
  run_script
  assert_equal "$STATUS" 0
  assert_contains "$OUTPUT" "a) pacman cache: skipped, paccache is not installed"
  assert_contains "$OUTPUT" "c) AUR build folders: skipped, paru is not installed"
  assert_contains "$OUTPUT" "d) Docker: skipped, docker is not installed"
  assert_contains "$OUTPUT" "e) Flatpak: skipped, flatpak is not installed"
}

test_missing_tools_are_skipped_in_clean_mode() {
  run_script --clean </dev/null
  assert_equal "$STATUS" 0
  assert_contains "$OUTPUT" "d) Docker: skipped, docker is not installed"
  assert_contains "$OUTPUT" "e) Flatpak: skipped, flatpak is not installed"
}

test_scan_only_removes_nothing() {
  fill_every_group
  local before after
  before="$(tree_state)"
  run_script <<<$'y\ny\ny\ny\ny\ny\ny\ny\ny\ny'
  after="$(tree_state)"
  assert_equal "$STATUS" 0
  assert_equal "$after" "$before"
  assert_contains "$OUTPUT" "Scan only, nothing is removed."
  assert_not_contains "$OUTPUT" "Remove? [y/N]"
  assert_not_contains "$(calls)" "sudo"
  assert_not_contains "$(calls)" "prune"
  assert_not_contains "$(calls)" "uninstall"
  assert_not_contains "$(calls)" "-Rns"
  assert_not_contains "$(calls)" "paccache -r"
  assert_not_contains "$(calls)" "gio"
}

test_scan_lists_every_group() {
  fill_every_group
  run_script
  assert_contains "$OUTPUT" "a) pacman cache: packages no longer installed: 2 files, 10.00 MiB. Old versions beyond the last 2: nothing."
  assert_contains "$OUTPUT" "b) orphan packages: 1 to remove (2.0 MiB). Kept as protected: linux-lts"
  assert_contains "$OUTPUT" "c) AUR build folders of packages no longer installed: 1 ("
  assert_contains "$OUTPUT" "d) Docker: dangling images no container uses: 1 (10MB). Dangling images kept because a container uses them: 1. Build cache: 300MB. All images 2GB, reclaimable 1GB (50%). Stopped containers, named images and volumes always stay."
  assert_contains "$OUTPUT" "d) note: Docker uses the containerd image store, so images live in /var/lib/containerd."
  assert_contains "$OUTPUT" "e) Flatpak: 3 runtimes installed."
  assert_contains "$OUTPUT" "f) JetBrains folders of IDE versions no longer installed: 1 ("
  assert_contains "$OUTPUT" "g) Trash: 2 items"
  assert_contains "$OUTPUT" "h) thumbnails whose original file no longer exists: 1 of 1 ("
}

test_protected_orphans_are_never_offered() {
  printf '%s\n' linux-lts intel-ucode amd-ucode linux-firmware-whence nvidia-utils mkinitcpio-busybox limine-snapper-sync plymouth-theme-x systemd-ukify snapd python-build asar >"$FAKE_DIR/orphans"
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "b) orphan packages: 2 to remove (4.0 MiB). Kept as protected: linux-lts intel-ucode amd-ucode linux-firmware-whence nvidia-utils mkinitcpio-busybox limine-snapper-sync plymouth-theme-x systemd-ukify snapd"
  assert_contains "$(calls)" "sudo pacman -Rns python-build asar"
  assert_not_contains "$(calls)" "--noconfirm"
  assert_equal "$(grep -c -- '-Rns' "$CALL_LOG")" 2
  assert_contains "$OUTPUT" "b) removed 2 orphan packages"
}

test_orphans_kept_on_no() {
  printf 'python-build\n' >"$FAKE_DIR/orphans"
  run_script --clean <<<"n"
  assert_contains "$OUTPUT" "b) kept the orphan packages"
  assert_not_contains "$(calls)" "sudo"
}

test_empty_orphan_list_is_handled() {
  run_script --clean </dev/null
  assert_equal "$STATUS" 0
  assert_contains "$OUTPUT" "b) orphan packages: none to remove. Kept as protected: none"
  assert_not_contains "$(calls)" "-Qi"
  assert_not_contains "$(calls)" "-Rns"
}

make_clone() {
  local folder=$1 base=$2
  shift 2
  mkdir -p "$HOME/.cache/paru/clone/$folder"
  {
    printf 'pkgbase = %s\n\tpkgver = 1.0\n\tpkgrel = 1\n\n' "$base"
    for name in "$@"; do
      printf 'pkgname = %s\n' "$name"
    done
  } >"$HOME/.cache/paru/clone/$folder/.SRCINFO"
}

test_paru_clone_matching_handles_split_packages() {
  stub_paru
  make_clone single single single
  make_clone split-base split-base split-a split-b
  make_clone gone gone gone
  make_clone gone-split gone-split gone-a gone-b
  mkdir -p "$HOME/.cache/paru/clone/no-srcinfo"
  printf '%s\n' single split-b unrelated >"$FAKE_DIR/installed"
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "c) AUR build folders of packages no longer installed: 2 ("
  assert_contains "$OUTPUT" "Kept because they have no .SRCINFO: 1"
  assert_missing "$HOME/.cache/paru/clone/gone"
  assert_missing "$HOME/.cache/paru/clone/gone-split"
  assert_exists "$HOME/.cache/paru/clone/single"
  assert_exists "$HOME/.cache/paru/clone/split-base"
  assert_exists "$HOME/.cache/paru/clone/no-srcinfo"
  assert_contains "$OUTPUT" "c) removed $HOME/.cache/paru/clone/gone"
}

test_paru_clone_kept_on_no() {
  stub_paru
  make_clone gone gone gone
  run_script --clean <<<"n"
  assert_exists "$HOME/.cache/paru/clone/gone"
  assert_contains "$OUTPUT" "c) kept the AUR build folders"
}

test_paru_clone_skipped_while_makepkg_runs() {
  stub_paru
  make_clone gone gone gone
  export FAKE_RUNNING=makepkg
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "c) AUR build folders: skipped, a makepkg or paru process is running"
  assert_exists "$HOME/.cache/paru/clone/gone"
}

test_paru_clone_skipped_while_paru_runs() {
  stub_paru
  make_clone gone gone gone
  export FAKE_RUNNING=paru
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "c) AUR build folders: skipped, a makepkg or paru process is running"
  assert_exists "$HOME/.cache/paru/clone/gone"
}

test_jetbrains_only_versions_not_installed_are_offered() {
  local apps="$HOME/.local/share/Jetbrains/Toolbox/apps"
  mkdir -p "$apps/intellij-idea" "$HOME/.local/share/JetBrains/Toolbox"
  printf '{\n  "install_location": "~/.local/share/Jetbrains/Toolbox/apps",\n  "autostart": false\n}\n' >"$HOME/.local/share/JetBrains/Toolbox/.settings.json"
  printf '{\n  "name": "IntelliJ IDEA",\n  "dataDirectoryName": "IntelliJIdea2026.2",\n  "version": "2026.2.3"\n}\n' >"$apps/intellij-idea/product-info.json"
  mkdir -p "$HOME/.cache/JetBrains/"{IntelliJIdea2026.2,IntelliJIdea2025.3,PyCharm2025.1,Toolbox,Daemon,acp-agents}
  mkdir -p "$HOME/.local/share/JetBrains/"{IntelliJIdea2026.2,IntelliJIdea2025.3,consentOptions}
  mkdir -p "$HOME/.config/JetBrains/"{IntelliJIdea2026.2,IntelliJIdea2025.3}
  run_script --clean <<<$'y\nn\ny\ny'
  assert_contains "$OUTPUT" "f) JetBrains folders of IDE versions no longer installed: 4 ("
  assert_contains "$OUTPUT" "Installed versions: IntelliJIdea2026.2"
  assert_missing "$HOME/.cache/JetBrains/IntelliJIdea2025.3"
  assert_exists "$HOME/.cache/JetBrains/PyCharm2025.1"
  assert_contains "$OUTPUT" "f) kept $HOME/.cache/JetBrains/PyCharm2025.1"
  assert_missing "$HOME/.local/share/JetBrains/IntelliJIdea2025.3"
  assert_missing "$HOME/.config/JetBrains/IntelliJIdea2025.3"
  assert_exists "$HOME/.cache/JetBrains/IntelliJIdea2026.2"
  assert_exists "$HOME/.local/share/JetBrains/IntelliJIdea2026.2"
  assert_exists "$HOME/.config/JetBrains/IntelliJIdea2026.2"
  assert_exists "$HOME/.cache/JetBrains/Toolbox"
  assert_exists "$HOME/.cache/JetBrains/Daemon"
  assert_exists "$HOME/.cache/JetBrains/acp-agents"
  assert_exists "$HOME/.local/share/JetBrains/Toolbox/.settings.json"
  assert_exists "$HOME/.local/share/JetBrains/consentOptions"
  assert_exists "$apps/intellij-idea/product-info.json"
}

test_jetbrains_skipped_when_no_ide_is_found() {
  mkdir -p "$HOME/.cache/JetBrains/IntelliJIdea2025.3"
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "f) JetBrains: skipped, no installed IDE was found"
  assert_exists "$HOME/.cache/JetBrains/IntelliJIdea2025.3"
}

test_thumbnails_only_for_missing_originals() {
  local thumbs="$HOME/.cache/thumbnails"
  mkdir -p "$HOME/Pictures"
  printf 'x' >"$HOME/Pictures/kept photo.jpg"
  printf 'x' >"$HOME/Pictures/kept.jpg"
  make_png "$thumbs/normal/text-present.png" tEXt "file://$HOME/Pictures/kept.jpg"
  make_png "$thumbs/large/text-missing.png" tEXt "file:///nowhere/gone.jpg"
  make_png "$thumbs/normal/zip-missing.png" zTXt "file:///nowhere/gone%20photo.jpg"
  make_png "$thumbs/x-large/zip-present.png" zTXt "file://$HOME/Pictures/kept%20photo.jpg"
  make_png "$thumbs/normal/web.png" tEXt "https://example.org/gone.jpg"
  make_png "$thumbs/fail/gnome-thumbnail-factory/no-uri.png" none
  run_script
  assert_contains "$OUTPUT" "h) thumbnails whose original file no longer exists: 2 of 6 ("
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "  /nowhere/gone photo.jpg"
  assert_contains "$OUTPUT" "h) removed 2 thumbnails"
  assert_missing "$thumbs/large/text-missing.png"
  assert_missing "$thumbs/normal/zip-missing.png"
  assert_exists "$thumbs/normal/text-present.png"
  assert_exists "$thumbs/x-large/zip-present.png"
  assert_exists "$thumbs/normal/web.png"
  assert_exists "$thumbs/fail/gnome-thumbnail-factory/no-uri.png"
}

test_thumbnails_kept_on_no() {
  make_png "$HOME/.cache/thumbnails/normal/gone.png" zTXt "file:///nowhere/gone.jpg"
  run_script --clean <<<"n"
  assert_contains "$OUTPUT" "h) kept the thumbnails"
  assert_exists "$HOME/.cache/thumbnails/normal/gone.png"
}

fill_trash() {
  local trash="$HOME/.local/share/Trash"
  mkdir -p "$trash/files/folder/inner" "$trash/info"
  printf 'x' >"$trash/files/file.txt"
  printf 'x' >"$trash/files/folder/inner/data"
  printf '[Trash Info]\n' >"$trash/info/file.txt.trashinfo"
  printf '[Trash Info]\n' >"$trash/info/folder.trashinfo"
}

test_trash_kept_on_no() {
  fill_trash
  run_script --clean <<<"n"
  assert_contains "$OUTPUT" "g) Trash: 2 items"
  assert_contains "$OUTPUT" "g) kept the Trash"
  assert_exists "$HOME/.local/share/Trash/files/file.txt"
  assert_not_contains "$(calls)" "gio"
}

test_trash_emptied_only_in_home_and_gio_never_called() {
  fill_trash
  stub_gio 0
  run_script --clean <<<"y"
  assert_not_contains "$(calls)" "gio"
  assert_contains "$OUTPUT" "g) emptied $HOME/.local/share/Trash"
  assert_contains "$OUTPUT" "g) Trash now holds 0 items"
  assert_missing "$HOME/.local/share/Trash/files/file.txt"
  assert_missing "$HOME/.local/share/Trash/files/folder"
  assert_missing "$HOME/.local/share/Trash/info/file.txt.trashinfo"
  assert_exists "$HOME/.local/share/Trash/files"
  assert_exists "$HOME/.local/share/Trash/info"
}

test_docker_prunes_only_dangling_images_and_build_cache() {
  stub_docker
  run_script --clean <<<$'y\ny'
  assert_contains "$OUTPUT" "  sha256aaa 10MB"
  assert_not_contains "$OUTPUT" "  sha256bbb"
  assert_contains "$(calls)" "docker image prune"
  assert_contains "$(calls)" "docker builder prune"
  assert_not_contains "$(calls)" "image prune -a"
  assert_not_contains "$(calls)" "container prune"
  assert_not_contains "$(calls)" "system prune"
  assert_not_contains "$(calls)" "volume prune"
  assert_not_contains "$(calls)" "--force"
}

test_docker_kept_on_no() {
  stub_docker
  run_script --clean <<<$'n\nn'
  assert_contains "$OUTPUT" "d) kept the dangling images"
  assert_contains "$OUTPUT" "d) kept the build cache"
  assert_not_contains "$(calls)" "prune"
}

test_paccache_clean_runs_as_root_only_for_groups_with_candidates() {
  stub_paccache
  run_script --clean <<<"y"
  assert_contains "$OUTPUT" "old-tool-1.0-1-x86_64.pkg.tar.zst"
  assert_contains "$(calls)" "sudo paccache -ruk0"
  assert_not_contains "$(calls)" "paccache -rk2"
  assert_contains "$OUTPUT" "a) old package versions beyond the last 2: nothing to remove"
}

test_flatpak_clean_lets_flatpak_ask() {
  stub_flatpak
  run_script --clean </dev/null
  assert_contains "$(calls)" "flatpak uninstall --unused"
  assert_not_contains "$(calls)" "-y"
  assert_not_contains "$(calls)" "--noninteractive"
  assert_not_contains "$(calls)" "--assumeyes"
}

run_test() {
  current_test=$1
  if ( setup; "$current_test" ); then
    passed=$(( passed + 1 ))
    printf 'PASS %s\n' "$current_test"
  else
    failed=$(( failed + 1 ))
    failures+=("$current_test")
  fi
}

main() {
  if [[ ! -f /.dockerenv ]]; then
    printf 'These tests run only inside the container that run-tests.sh creates.\n' >&2
    return 2
  fi
  local name
  for name in $(declare -F | awk '$3 ~ /^test_/ { print $3 }'); do
    run_test "$name"
  done
  printf '%d passed, %d failed\n' "$passed" "$failed"
  if (( failed > 0 )); then
    printf 'failed: %s\n' "${failures[@]}"
    return 1
  fi
}

main "$@"
