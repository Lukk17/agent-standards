# Bash Checklist

Run it before calling a script done. The rules behind each item are in [SKILL.md](../SKILL.md).

- [ ] `set -euo pipefail` and `IFS=$'\n\t'` immediately after the shebang.
- [ ] Every variable expansion quoted, every test using `[[ ]]`.
- [ ] Required commands checked with `command -v` before any logic.
- [ ] Arguments validated at entry, `-h` and `--help` implemented, usage matches the header block.
- [ ] `trap cleanup EXIT` removes every temp file and lock.
- [ ] Temp paths created with `mktemp`, never hardcoded.
- [ ] No secret in a positional argument, an echo, or a log line.
- [ ] Exit codes documented in the header, functions return rather than exit, except `usage` and the `EXIT` trap.
- [ ] ShellCheck passes with zero findings, every suppression justified inline.
