#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: run-tests.sh
# Description: Runs the cleanup-leftovers.sh tests and ShellCheck in throwaway containers with no network and no host folder mounted, then removes the containers.
# Usage: run-tests.sh
# Requires: Bash 4.4 or newer, docker, the images archlinux:latest and koalaman/shellcheck:stable (pulled when missing)
# Exit codes:
#   0  the tests and ShellCheck passed
#   1  a test or ShellCheck failed
#   2  docker is not installed
# The pulled images stay. Remove them with: docker image rm archlinux:latest koalaman/shellcheck:stable
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly SCRIPTS_DIR
readonly TEST_IMAGE="archlinux:latest"
readonly SHELLCHECK_IMAGE="koalaman/shellcheck:stable"
readonly TEST_CONTAINER="arch-linux-cleanup-leftovers-test-$$"
readonly SHELLCHECK_CONTAINER="arch-linux-cleanup-leftovers-shellcheck-$$"

cleanup() {
  local exit_code=$?
  docker rm -f "$TEST_CONTAINER" "$SHELLCHECK_CONTAINER" >/dev/null 2>&1 || true
  exit "$exit_code"
}
trap cleanup EXIT

run_in_container() {
  local name=$1 image=$2
  shift 2
  docker create --network none --name "$name" "$image" "$@" >/dev/null
  docker cp "$SCRIPTS_DIR/." "$name:/work"
  docker start --attach "$name"
}

main() {
  if ! command -v docker >/dev/null 2>&1; then
    printf 'docker is not installed\n' >&2
    return 2
  fi
  local status=0
  run_in_container "$SHELLCHECK_CONTAINER" "$SHELLCHECK_IMAGE" --severity=style /work/cleanup-leftovers.sh /work/tests/run-tests.sh /work/tests/test-cleanup-leftovers.sh || status=1
  if (( status == 0 )); then
    printf 'shellcheck: no findings\n'
  fi
  run_in_container "$TEST_CONTAINER" "$TEST_IMAGE" bash /work/tests/test-cleanup-leftovers.sh || status=1
  return "$status"
}

main "$@"
